from django import forms
from .models import RegisteredUser

class CandidateForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'enter valid email to send result'}))
    job_description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Example :Python Developer'}))

class AnswerForm(forms.Form):
    answer = forms.CharField(widget=forms.Textarea)

class ProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = RegisteredUser
        fields = ['name', 'mobile', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border rounded-lg px-4 py-2',
                'placeholder': 'Enter your full name'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'w-full border rounded-lg px-4 py-2',
                'placeholder': 'Enter your mobile number'
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full border rounded-lg px-4 py-2'
            })
        }