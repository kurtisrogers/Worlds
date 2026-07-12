"""Account views."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from accounts.models import AuthorProfile


class WorldsLoginView(LoginView):
    template_name = "accounts/login.html"


class WorldsLogoutView(LogoutView):
    next_page = reverse_lazy("stories:home")


def register(request):
    if request.user.is_authenticated:
        return redirect("stories:dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to Worlds! Start writing your story.")
            return redirect("stories:dashboard")
    else:
        form = UserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    profile_obj, _ = AuthorProfile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.username},
    )
    if request.method == "POST":
        profile_obj.display_name = request.POST.get("display_name", "")
        profile_obj.bio = request.POST.get("bio", "")
        profile_obj.website = request.POST.get("website", "")
        profile_obj.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {"profile": profile_obj})
