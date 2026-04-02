from django.db import models
from django.contrib.auth.models import User


class SimulationRun(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='simulation_runs')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')

    # Input parameters (stored as JSON)
    input_payload = models.JSONField(default=dict)

    # Result summary
    mean_yield = models.FloatField(null=True, blank=True)
    std_yield = models.FloatField(null=True, blank=True)
    best_yield = models.FloatField(null=True, blank=True)
    worst_yield = models.FloatField(null=True, blank=True)
    total_dies = models.IntegerField(null=True, blank=True)

    # Full result data (pareto contributors, all_yields sample, etc.)
    result_payload = models.JSONField(default=dict, blank=True)

    # Paths to generated image artifacts (relative to MEDIA_ROOT)
    wafer_map_image = models.ImageField(upload_to='simulation_runs/', null=True, blank=True)
    pareto_image = models.ImageField(upload_to='simulation_runs/', null=True, blank=True)

    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Run #{self.pk} by {self.user.username} ({self.status})'
