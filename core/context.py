from .models import Wedding


def wedding(request):
    """Shared branding and limited attendance navigation context."""
    user = getattr(request, "user", None)
    context = {"can_view_attendance": False}
    if user is not None and user.is_authenticated:
        context["can_view_attendance"] = (
            user.is_staff or user.groups.filter(name__startswith="Attendance Viewer:").exists() or user.groups.filter(name="Wedding Owner").exists()
        )
        if user.is_staff:
            context["wedding"] = Wedding.for_user(user) or Wedding.objects.first()
        elif user.groups.filter(name="Wedding Owner").exists():
            context["wedding"] = Wedding.for_user(user)
    return context
