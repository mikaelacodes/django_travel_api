from django.urls import path  # noqa: F401 (kept for when app-specific routes are added)

app_name = 'budgets'

# Budgets and expenses are served by their ViewSets via the main router, so
# there are no extra function/class routes here yet. The namespace stays defined
# for consistency with the other apps.
urlpatterns = []
