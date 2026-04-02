"""Views for the simulator app."""

import csv
import io
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import SimulationRun
from .services import DEFAULT_PROCESS_PARAMS, DEFAULT_SPEC_LIMITS, run_simulation


# ── Dashboard (home) ────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    runs = SimulationRun.objects.filter(user=request.user).order_by('-created_at')
    last_run = runs.first()
    completed = runs.filter(status='completed')
    context = {
        'last_run': last_run,
        'total_runs': runs.count(),
        'completed_runs': completed.count(),
        'best_yield': max((r.best_yield for r in completed if r.best_yield), default=None),
        'recent_runs': runs[:5],
    }
    return render(request, 'simulator/dashboard.html', context)


# ── Simulation configuration + run ─────────────────────────────────────────

@login_required
def simulate_config(request):
    """Show configuration form. On POST, kick off simulation synchronously."""
    params = DEFAULT_PROCESS_PARAMS
    spec = DEFAULT_SPEC_LIMITS
    if request.method == 'POST':
        input_payload = {
            'wafer_diameter_mm': float(request.POST.get('wafer_diameter_mm', 300)),
            'die_size_mm': float(request.POST.get('die_size_mm', 5.0)),
            'mc_runs': int(request.POST.get('mc_runs', 10000)),
            # per-parameter overrides
            'vth0_nominal': float(request.POST.get('vth0_nominal', params['vth0']['nominal'])),
            'vth0_sigma': float(request.POST.get('vth0_sigma', params['vth0']['sigma'])),
            'tox_nominal': float(request.POST.get('tox_nominal', params['tox']['nominal'])),
            'tox_sigma': float(request.POST.get('tox_sigma', params['tox']['sigma'])),
            'u0_nominal': float(request.POST.get('u0_nominal', params['u0']['nominal'])),
            'u0_sigma': float(request.POST.get('u0_sigma', params['u0']['sigma'])),
        }
        sim_run = SimulationRun.objects.create(user=request.user, input_payload=input_payload)
        try:
            run_simulation(sim_run)
        except Exception:
            messages.error(request, f'Simulation failed: {sim_run.error_message}')
            return redirect('simulator:history')
        return redirect('simulator:results', pk=sim_run.pk)

    context = {
        'params': params,
        'spec': spec,
    }
    return render(request, 'simulator/simulate_config.html', context)


# ── Results ─────────────────────────────────────────────────────────────────

@login_required
def results(request, pk):
    sim_run = get_object_or_404(SimulationRun, pk=pk, user=request.user)
    return render(request, 'simulator/results.html', {'run': sim_run})


# ── History ──────────────────────────────────────────────────────────────────

@login_required
def history(request):
    runs = SimulationRun.objects.filter(user=request.user).order_by('-created_at')
    completed = runs.filter(status='completed')
    avg_yield = None
    if completed.exists():
        vals = [r.mean_yield for r in completed if r.mean_yield is not None]
        if vals:
            avg_yield = sum(vals) / len(vals)
    context = {
        'runs': runs,
        'total_runs': runs.count(),
        'avg_yield': avg_yield,
    }
    return render(request, 'simulator/history.html', context)


# ── Export ───────────────────────────────────────────────────────────────────

@login_required
def export_csv(request, pk):
    sim_run = get_object_or_404(SimulationRun, pk=pk, user=request.user)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="run_{sim_run.pk}_results.csv"'

    writer = csv.writer(response)
    writer.writerow(['PatternIQ — Simulation Run Export'])
    writer.writerow(['Run ID', f'#{sim_run.pk}'])
    writer.writerow(['User', sim_run.user.username])
    writer.writerow(['Date', sim_run.created_at.strftime('%Y-%m-%d %H:%M UTC')])
    writer.writerow(['Status', sim_run.status])
    writer.writerow([])

    writer.writerow(['=== Inputs ==='])
    for k, v in sim_run.input_payload.items():
        writer.writerow([k, v])
    writer.writerow([])

    writer.writerow(['=== Results Summary ==='])
    writer.writerow(['Mean Yield (%)', f'{sim_run.mean_yield:.2f}' if sim_run.mean_yield is not None else 'N/A'])
    writer.writerow(['Std Dev (%)',    f'{sim_run.std_yield:.2f}'  if sim_run.std_yield  is not None else 'N/A'])
    writer.writerow(['Best Yield (%)', f'{sim_run.best_yield:.2f}' if sim_run.best_yield is not None else 'N/A'])
    writer.writerow(['Worst Yield (%)',f'{sim_run.worst_yield:.2f}'if sim_run.worst_yield is not None else 'N/A'])
    writer.writerow(['Total Dies',    sim_run.total_dies or 'N/A'])
    writer.writerow([])

    pareto = sim_run.result_payload.get('pareto', [])
    if pareto:
        writer.writerow(['=== Pareto Analysis ==='])
        writer.writerow(['Parameter', 'Yield Loss (%)'])
        for name, loss in pareto:
            writer.writerow([name, loss])
        writer.writerow([])

    yield_sample = sim_run.result_payload.get('yield_sample', [])
    if yield_sample:
        writer.writerow(['=== Yield Sample (first 500 MC iterations) ==='])
        writer.writerow(['Iteration', 'Yield (%)'])
        for i, y in enumerate(yield_sample, 1):
            writer.writerow([i, y])

    return response


@login_required
def export_pdf(request, pk):
    sim_run = get_object_or_404(SimulationRun, pk=pk, user=request.user)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    heading = ParagraphStyle('Heading', parent=styles['Heading1'],
                             textColor=colors.HexColor('#006948'), spaceAfter=6)
    sub = ParagraphStyle('Sub', parent=styles['Heading2'],
                         textColor=colors.HexColor('#545f73'), spaceAfter=4)
    normal = styles['Normal']

    story = []
    story.append(Paragraph('PatternIQ — Simulation Run Report', heading))
    story.append(Paragraph(
        f'Run #{sim_run.pk} &nbsp;|&nbsp; {sim_run.user.username} &nbsp;|&nbsp; '
        f'{sim_run.created_at.strftime("%Y-%m-%d %H:%M UTC")} &nbsp;|&nbsp; {sim_run.status.upper()}',
        normal,
    ))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph('Simulation Inputs', sub))
    inp_data = [['Parameter', 'Value']] + [[k, str(v)] for k, v in sim_run.input_payload.items()]
    inp_table = Table(inp_data, colWidths=[8*cm, 8*cm])
    inp_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#eceef0')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.HexColor('#006948')),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fb')]),
        ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#bccac0')),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ]))
    story.append(inp_table)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph('Results Summary', sub))
    def _fmt(v):
        return f'{v:.2f}' if v is not None else 'N/A'
    res_data = [
        ['Metric', 'Value'],
        ['Mean Yield (%)', _fmt(sim_run.mean_yield)],
        ['Std Dev (%)',    _fmt(sim_run.std_yield)],
        ['Best Yield (%)', _fmt(sim_run.best_yield)],
        ['Worst Yield (%)',_fmt(sim_run.worst_yield)],
        ['Total Dies',     str(sim_run.total_dies or 'N/A')],
    ]
    res_table = Table(res_data, colWidths=[8*cm, 8*cm])
    res_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#eceef0')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.HexColor('#006948')),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fb')]),
        ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#bccac0')),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ]))
    story.append(res_table)
    story.append(Spacer(1, 0.5*cm))

    pareto = sim_run.result_payload.get('pareto', [])
    if pareto:
        story.append(Paragraph('Pareto Analysis — Yield Loss by Parameter', sub))
        pareto_data = [['Parameter', 'Yield Loss (%)']] + [[n, str(l)] for n, l in pareto]
        p_table = Table(pareto_data, colWidths=[12*cm, 4*cm])
        p_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#eceef0')),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fb')]),
            ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#bccac0')),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ]))
        story.append(p_table)
        story.append(Spacer(1, 0.5*cm))

    for label, field in [('Wafer Map & Yield Distribution', sim_run.wafer_map_image),
                          ('Pareto Chart', sim_run.pareto_image)]:
        if field:
            story.append(Paragraph(label, sub))
            try:
                img = RLImage(field.path, width=16*cm, height=7*cm)
                story.append(img)
                story.append(Spacer(1, 0.5*cm))
            except Exception:
                story.append(Paragraph(f'(Image not available: {field.name})', normal))

    doc.build(story)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="run_{sim_run.pk}_report.pdf"'
    return response

