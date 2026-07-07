from django.db import models
from django.contrib.auth.models import User


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Movie(models.Model):
    RATING_CHOICES = [
        ('G', 'G'),
        ('PG', 'PG'),
        ('PG-13', 'PG-13'),
        ('R', 'R'),
        ('NC-17', 'NC-17'),
    ]

    title           = models.CharField(max_length=255)
    description     = models.TextField(blank=True)
    release_year    = models.IntegerField(default=2024)
    duration_mins   = models.IntegerField(default=0)
    rating          = models.CharField(max_length=10, choices=RATING_CHOICES, default='PG-13')
    genres          = models.ManyToManyField(Genre, blank=True)

    # Categorization
    language        = models.CharField(max_length=50, default='English')
    country         = models.CharField(max_length=50, default='USA')
    popularity      = models.FloatField(default=0.0)
    is_trending     = models.BooleanField(default=False)
    is_featured     = models.BooleanField(default=False)
    award_winning   = models.BooleanField(default=False)
    family_friendly = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=True)

    # Skip intro / recap metadata
    intro_start     = models.IntegerField(default=0, help_text="Intro start in seconds")
    intro_end       = models.IntegerField(default=0, help_text="Intro end in seconds")
    recap_start     = models.IntegerField(default=0, help_text="Recap start in seconds")
    recap_end       = models.IntegerField(default=0, help_text="Recap end in seconds")

    # Episode linking
    next_episode    = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='previous_episode'
    )

    # Media URLs
    thumbnail_url   = models.URLField(blank=True)
    backdrop_url    = models.URLField(blank=True)
    trailer_url     = models.URLField(blank=True)
    hls_stream_url  = models.URLField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class VideoQuality(models.Model):
    """Multiple quality streams for a movie (480p, 720p, 1080p, etc.)"""
    movie       = models.ForeignKey(Movie, related_name='qualities', on_delete=models.CASCADE)
    label       = models.CharField(max_length=20)   # e.g. "1080p", "720p", "Auto"
    resolution  = models.CharField(max_length=20, blank=True)  # e.g. "1920x1080"
    bitrate     = models.CharField(max_length=20, blank=True)  # e.g. "5000kbps"
    url         = models.URLField()
    is_default  = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.movie.title} — {self.label}"


class Subtitle(models.Model):
    """WebVTT subtitle tracks for a movie"""
    movie       = models.ForeignKey(Movie, related_name='subtitles', on_delete=models.CASCADE)
    language    = models.CharField(max_length=50)
    language_code = models.CharField(max_length=10, default='en')  # ISO 639-1
    file_url    = models.URLField()  # WebVTT file
    is_default  = models.BooleanField(default=False)
    is_forced   = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.movie.title} — {self.language}"


class AudioTrack(models.Model):
    """Multiple audio tracks (dubbed languages) for a movie"""
    movie           = models.ForeignKey(Movie, related_name='audio_tracks', on_delete=models.CASCADE)
    language        = models.CharField(max_length=50)
    language_code   = models.CharField(max_length=10, default='en')
    stream_url      = models.URLField()
    is_default      = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.movie.title} — {self.language}"


class UserProfile(models.Model):
    """
    One User can have multiple UserProfiles (like Netflix profiles).
    is_main = True marks the account owner's primary profile.
    """
    AVATAR_CHOICES = [
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'),
        ('E', 'E'), ('F', 'F'), ('G', 'G'), ('H', 'H'),
    ]

    user                = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')
    name                = models.CharField(max_length=100)
    pin                 = models.CharField(max_length=128, blank=True, null=True)  # 4-digit PIN lock
    age                 = models.IntegerField(default=18)
    mobile              = models.CharField(max_length=20, blank=True)
    country             = models.CharField(max_length=50, blank=True)
    preferred_language  = models.CharField(max_length=50, default='English')
    avatar              = models.CharField(max_length=5, choices=AVATAR_CHOICES, default='A')
    is_main             = models.BooleanField(default=False)
    favorite_genres     = models.ManyToManyField(Genre, blank=True, related_name='fan_profiles')

    def __str__(self):
        return f"{self.user.username} — {self.name}"

    def save(self, *args, **kwargs):
        if self.pin and not ('$' in self.pin):
            from django.contrib.auth.hashers import make_password
            self.pin = make_password(self.pin)
        super().save(*args, **kwargs)


class Watchlist(models.Model):
    profile     = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='watchlist')
    movie       = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'movie')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.profile.name} → {self.movie.title}"


class WatchHistory(models.Model):
    profile         = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='history')
    movie           = models.ForeignKey(Movie, on_delete=models.CASCADE)
    progress_secs   = models.IntegerField(default=0)
    completed       = models.BooleanField(default=False)
    watched_at      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('profile', 'movie')
        ordering = ['-watched_at']

    def __str__(self):
        return f"{self.profile.name} → {self.movie.title} ({self.progress_secs}s)"