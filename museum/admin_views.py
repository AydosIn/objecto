from django.contrib import admin
from django.views.generic import TemplateView

from .analytics import DEFAULT_PERIOD, PERIODS, build_report


class AnalyticsView(TemplateView):
    """Usage, speed, failures and cost of Gemini calls. Mounted in config/urls.py
    behind admin.site.admin_view, so only logged-in staff can open it."""

    template_name = 'admin/museum/analytics.html'

    def get_context_data(self, **kwargs):
        try:
            days = int(self.request.GET.get('days', DEFAULT_PERIOD))
        except ValueError:
            days = DEFAULT_PERIOD
        if days not in PERIODS:
            days = DEFAULT_PERIOD

        return {
            **super().get_context_data(**kwargs),
            # Header, sidebar and theme toggle of the normal admin pages.
            **admin.site.each_context(self.request),
            'title': 'Analytics',
            'periods': PERIODS,
            'report': build_report(days),
        }
