from django.db import models

class Candidate(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    job_description = models.TextField()

    def __str__(self):
        return self.name


class InterviewResponse(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    score = models.IntegerField(null=True, blank=True)


class RegisteredUser(models.Model):
    keycloak_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)

    # AI Interviewer specific fields
    name = models.CharField(max_length=100, blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    image = models.ImageField(upload_to='user_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.username or self.name or "User"