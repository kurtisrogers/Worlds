"""Staff administration views for support, moderators, and super admins."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import PlatformRole, UserAccount
from accounts.roles import role_required, sync_django_staff_flags
from engagement.models import ChapterComment
from payments.models import Transaction
from stories.models import ReaderSubscription, Story

User = get_user_model()


@login_required
@role_required(PlatformRole.SUPPORT)
def staff_dashboard(request):
    stats = {
        "users": User.objects.count(),
        "stories": Story.objects.count(),
        "active_subscriptions": ReaderSubscription.objects.filter(
            status=ReaderSubscription.Status.ACTIVE
        ).count(),
        "pending_comments": ChapterComment.objects.count(),
        "recent_transactions": Transaction.objects.count(),
    }
    staff_accounts = UserAccount.objects.filter(
        platform_role__in=[
            PlatformRole.SUPPORT,
            PlatformRole.MODERATOR,
            PlatformRole.SUPER_ADMIN,
        ]
    ).select_related("user")
    return render(
        request,
        "staff/dashboard.html",
        {"stats": stats, "staff_accounts": staff_accounts},
    )


@login_required
@role_required(PlatformRole.SUPPORT)
def staff_users(request):
    query = request.GET.get("q", "")
    users = User.objects.select_related("account", "author_profile").annotate(
        story_count=Count("stories")
    )
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(account__platform_role__icontains=query)
        )
    return render(request, "staff/users.html", {"users": users[:50], "query": query})


@login_required
@role_required(PlatformRole.SUPPORT)
def staff_user_detail(request, username):
    user = get_object_or_404(
        User.objects.select_related("account", "author_profile"),
        username=username,
    )
    subscriptions = ReaderSubscription.objects.filter(reader=user).select_related(
        "story", "tier"
    )
    transactions = Transaction.objects.filter(user=user)[:20]
    stories = user.stories.all()[:10]
    return render(
        request,
        "staff/user_detail.html",
        {
            "profile_user": user,
            "subscriptions": subscriptions,
            "transactions": transactions,
            "stories": stories,
        },
    )


@login_required
@role_required(PlatformRole.SUPER_ADMIN)
def staff_set_role(request, username):
    if request.method != "POST":
        return redirect("staff:user_detail", username=username)

    user = get_object_or_404(User, username=username)
    account, _ = UserAccount.objects.get_or_create(user=user)
    new_role = request.POST.get("platform_role", PlatformRole.READER)
    if new_role in dict(PlatformRole.choices):
        account.platform_role = new_role
        account.save(update_fields=["platform_role", "updated_at"])
        sync_django_staff_flags(user)
        messages.success(
            request,
            f"Updated {username} to {account.get_platform_role_display()}.",
        )
    return redirect("staff:user_detail", username=username)


@login_required
@role_required(PlatformRole.MODERATOR)
def staff_comments(request):
    comments = ChapterComment.objects.select_related(
        "user", "chapter", "chapter__story"
    ).order_by("-created_at")[:100]
    return render(request, "staff/comments.html", {"comments": comments})


@login_required
@role_required(PlatformRole.MODERATOR)
def staff_delete_comment(request, comment_id):
    if request.method == "POST":
        comment = get_object_or_404(ChapterComment, pk=comment_id)
        comment.delete()
        messages.success(request, "Comment removed.")
    return redirect("staff:comments")
