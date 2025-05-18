from django.db import models

class Operation(models.Model):
    tool       = models.CharField(max_length=50)  # Increased max_length for tool name
    args       = models.JSONField()               # Arguments used for the tool
    in_hash    = models.CharField(max_length=64, null=True, blank=True) # SHA-256 hash of input file
    out_hash   = models.CharField(max_length=64, null=True, blank=True) # SHA-256 hash of output file
    status     = models.CharField(max_length=20, default="success") # e.g., success, error
    error_message = models.TextField(null=True, blank=True) # Details if an error occurred
    created_at = models.DateTimeField(auto_now_add=True) # Timestamp of the operation

    def __str__(self):
        return f"{self.tool} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
