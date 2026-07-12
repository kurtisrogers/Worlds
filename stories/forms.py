"""Story forms."""

from django import forms

from stories.models import Chapter, Story


class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ["title", "synopsis", "status", "content_source", "cover_image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your story title"}),
            "synopsis": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "content_source": forms.Select(attrs={"class": "form-select"}),
        }


class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = [
            "number",
            "title",
            "content",
            "is_published",
            "unlock_price_cents",
            "tier_required",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "content": forms.Textarea(attrs={"class": "form-input editor-content", "rows": 20}),
            "number": forms.NumberInput(attrs={"class": "form-input"}),
            "unlock_price_cents": forms.NumberInput(attrs={"class": "form-input", "placeholder": "e.g. 299 for $2.99"}),
            "tier_required": forms.Select(attrs={"class": "form-select"}),
        }
