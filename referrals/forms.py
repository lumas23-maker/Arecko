from django import forms
from .models import Story

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['business_name', 'story', 'media']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business Name'}),
            'story': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Describe your experience...', 'rows': 4}),
            'media': forms.FileInput(attrs={'class': 'form-control'}),
        }