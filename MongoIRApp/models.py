from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    content = models.TextField(blank=True)  # Store the parsed content
    upload_date = models.DateTimeField(auto_now_add=True)