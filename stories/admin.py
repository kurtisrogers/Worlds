from django.contrib import admin

from stories.models import (
    Chapter,
    ChapterFavourite,
    ChapterLike,
    ChapterRead,
    ChapterUnlock,
    ReaderSubscription,
    Story,
    SubscriptionTier,
)


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ["number", "title", "is_published", "tier_required", "unlock_price_cents"]


class SubscriptionTierInline(admin.TabularInline):
    model = SubscriptionTier
    extra = 0


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "status", "content_source", "updated_at"]
    list_filter = ["status", "content_source"]
    search_fields = ["title", "author__username"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ChapterInline, SubscriptionTierInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["story", "number", "title", "is_published", "tier_required"]
    list_filter = ["is_published", "tier_required"]


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ["story", "name", "price_cents"]


@admin.register(ReaderSubscription)
class ReaderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["reader", "story", "tier", "status", "started_at"]
    list_filter = ["status"]


@admin.register(ChapterUnlock)
class ChapterUnlockAdmin(admin.ModelAdmin):
    list_display = ["reader", "chapter", "amount_cents", "unlocked_at"]


@admin.register(ChapterRead)
class ChapterReadAdmin(admin.ModelAdmin):
    list_display = ["reader", "chapter", "read_at"]
    list_select_related = ["reader", "chapter"]


@admin.register(ChapterLike)
class ChapterLikeAdmin(admin.ModelAdmin):
    list_display = ["reader", "chapter", "liked_at"]
    list_select_related = ["reader", "chapter"]


@admin.register(ChapterFavourite)
class ChapterFavouriteAdmin(admin.ModelAdmin):
    list_display = ["reader", "chapter", "favourited_at"]
    list_select_related = ["reader", "chapter"]
