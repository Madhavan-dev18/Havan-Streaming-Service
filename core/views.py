from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q

from .models import (
    Movie, Genre, UserProfile,
    Watchlist, WatchHistory,
)
from .serializers import (
    RegisterSerializer, UserProfileSerializer, UserProfileUpdateSerializer,
    MovieSerializer, MovieListSerializer, GenreSerializer,
    WatchlistSerializer, WatchHistorySerializer,
)


# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access':  str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access':  str(refresh.access_token),
            })
        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


# ──────────────────────────────────────────────
# PROFILES
# ──────────────────────────────────────────────

class ProfileListView(APIView):
    """GET all profiles for the logged-in user. POST to create a new sub-profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profiles = UserProfile.objects.filter(user=request.user).order_by('-is_main', 'name')
        return Response(UserProfileSerializer(profiles, many=True).data)

    def post(self, request):
        # Limit to 5 profiles per account
        if UserProfile.objects.filter(user=request.user).count() >= 5:
            return Response({'detail': 'Maximum 5 profiles per account.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserProfileUpdateSerializer(data=request.data)
        if serializer.is_valid():
            profile = serializer.save(user=request.user, is_main=False)
            return Response(UserProfileSerializer(profile).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileDetailView(APIView):
    """GET / PATCH / DELETE a single profile."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_profile(self, pk, user):
        try:
            return UserProfile.objects.get(pk=pk, user=user)
        except UserProfile.DoesNotExist:
            return None

    def get(self, request, pk):
        profile = self._get_profile(pk, request.user)
        if not profile:
            return Response({'detail': 'Not found.'}, status=404)
        return Response(UserProfileSerializer(profile).data)

    def patch(self, request, pk):
        profile = self._get_profile(pk, request.user)
        if not profile:
            return Response({'detail': 'Not found.'}, status=404)
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserProfileSerializer(profile).data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        profile = self._get_profile(pk, request.user)
        if not profile:
            return Response({'detail': 'Not found.'}, status=404)
        if profile.is_main:
            return Response({'detail': 'Cannot delete the main profile.'}, status=400)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyPinView(APIView):
    """Verify a profile's PIN. Returns 200 on success, 403 on failure."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile_id = request.data.get('profile_id')
        pin = request.data.get('pin')
        try:
            profile = UserProfile.objects.get(id=profile_id, user=request.user)
            from django.contrib.auth.hashers import check_password
            if profile.pin and check_password(str(pin), profile.pin):
                return Response({'success': True})
            return Response({'success': False, 'detail': 'Invalid PIN.'}, status=status.HTTP_403_FORBIDDEN)
        except UserProfile.DoesNotExist:
            return Response({'detail': 'Profile not found.'}, status=404)


# ──────────────────────────────────────────────
# MOVIES
# ──────────────────────────────────────────────

class MovieListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Movie.objects.filter(is_active=True).prefetch_related('genres')

        # Filtering
        genre    = request.query_params.get('genre')
        language = request.query_params.get('language')
        country  = request.query_params.get('country')
        year     = request.query_params.get('year')
        rating   = request.query_params.get('rating')
        search   = request.query_params.get('search')

        if genre:
            qs = qs.filter(genres__name__iexact=genre)
        if language:
            qs = qs.filter(language__iexact=language)
        if country:
            qs = qs.filter(country__iexact=country)
        if year:
            qs = qs.filter(release_year=year)
        if rating:
            qs = qs.filter(rating=rating)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        # Category flags
        category = request.query_params.get('category')
        if category == 'trending':
            qs = qs.filter(is_trending=True)
        elif category == 'featured':
            qs = qs.filter(is_featured=True)
        elif category == 'award_winning':
            qs = qs.filter(award_winning=True)
        elif category == 'family_friendly':
            qs = qs.filter(family_friendly=True)
        elif category == 'recently_added':
            qs = qs.order_by('-created_at')[:20]

        # Sorting
        sort = request.query_params.get('sort', '-created_at')
        allowed_sorts = ['popularity', '-popularity', 'release_year', '-release_year',
                         'title', '-title', 'created_at', '-created_at']
        if sort in allowed_sorts:
            qs = qs.order_by(sort)

        return Response(MovieListSerializer(qs.distinct(), many=True).data)


class MovieDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            movie = Movie.objects.get(pk=pk, is_active=True)
        except Movie.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)
        return Response(MovieSerializer(movie).data)


class FeaturedMovieView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        movie = Movie.objects.filter(is_featured=True, is_active=True).order_by('?').first()
        if not movie:
            movie = Movie.objects.filter(is_active=True).order_by('-popularity').first()
        if not movie:
            return Response({'detail': 'No featured movie.'}, status=404)
        return Response(MovieSerializer(movie).data)


class RecommendedMoviesView(APIView):
    """Returns personalised recommendations based on profile's genre preferences and watch history."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile_id = request.headers.get('Profile-Id')
        try:
            profile = UserProfile.objects.get(id=profile_id, user=request.user)
        except (UserProfile.DoesNotExist, TypeError):
            return Response({'detail': 'Profile not found.'}, status=404)

        # Collect genre IDs from: explicit preferences + watched movies
        pref_genres = set(profile.favorite_genres.values_list('id', flat=True))
        watched_ids = set(
            WatchHistory.objects.filter(profile=profile)
            .values_list('movie__genres__id', flat=True)
        )
        all_genre_ids = pref_genres | watched_ids
        already_watched_movie_ids = set(
            WatchHistory.objects.filter(profile=profile).values_list('movie_id', flat=True)
        )

        qs = Movie.objects.filter(is_active=True)
        if all_genre_ids:
            qs = qs.filter(genres__id__in=all_genre_ids).exclude(id__in=already_watched_movie_ids)
        else:
            qs = qs.order_by('-popularity')

        qs = qs.distinct().order_by('-popularity')[:20]
        return Response(MovieListSerializer(qs, many=True).data)


class GenreListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(GenreSerializer(Genre.objects.all(), many=True).data)


# ──────────────────────────────────────────────
# WATCHLIST
# ──────────────────────────────────────────────

class WatchlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_profile(self, request):
        profile_id = request.headers.get('Profile-Id')
        try:
            return UserProfile.objects.get(id=profile_id, user=request.user)
        except (UserProfile.DoesNotExist, TypeError, ValueError):
            return None

    def get(self, request):
        profile = self._get_profile(request)
        if not profile:
            return Response({'detail': 'Profile-Id header required.'}, status=400)
        items = Watchlist.objects.filter(profile=profile).select_related('movie')
        return Response(WatchlistSerializer(items, many=True).data)

    def post(self, request):
        profile = self._get_profile(request)
        if not profile:
            return Response({'detail': 'Profile-Id header required.'}, status=400)
        movie_id = request.data.get('movie_id')
        try:
            movie = Movie.objects.get(id=movie_id, is_active=True)
        except Movie.DoesNotExist:
            return Response({'detail': 'Movie not found.'}, status=404)
        obj, created = Watchlist.objects.get_or_create(profile=profile, movie=movie)
        if not created:
            return Response({'detail': 'Already in watchlist.'}, status=400)
        return Response(WatchlistSerializer(obj).data, status=201)

    def delete(self, request):
        profile = self._get_profile(request)
        if not profile:
            return Response({'detail': 'Profile-Id header required.'}, status=400)
        movie_id = request.data.get('movie_id')
        deleted, _ = Watchlist.objects.filter(profile=profile, movie_id=movie_id).delete()
        if deleted:
            return Response(status=204)
        return Response({'detail': 'Not in watchlist.'}, status=404)


# ──────────────────────────────────────────────
# WATCH HISTORY
# ──────────────────────────────────────────────

class WatchHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_profile(self, request):
        profile_id = request.headers.get('Profile-Id')
        try:
            return UserProfile.objects.get(id=profile_id, user=request.user)
        except (UserProfile.DoesNotExist, TypeError, ValueError):
            return None

    def get(self, request):
        profile = self._get_profile(request)
        if not profile:
            return Response({'detail': 'Profile-Id header required.'}, status=400)
        items = WatchHistory.objects.filter(profile=profile).select_related('movie')
        return Response(WatchHistorySerializer(items, many=True).data)

    def post(self, request):
        profile = self._get_profile(request)
        if not profile:
            return Response({'detail': 'Profile-Id header required.'}, status=400)
        movie_id     = request.data.get('movie_id')
        progress     = int(request.data.get('progress_secs', 0))
        completed    = request.data.get('completed', False)
        try:
            movie = Movie.objects.get(id=movie_id)
        except Movie.DoesNotExist:
            return Response({'detail': 'Movie not found.'}, status=404)
        obj, _ = WatchHistory.objects.update_or_create(
            profile=profile, movie=movie,
            defaults={'progress_secs': progress, 'completed': completed},
        )
        return Response(WatchHistorySerializer(obj).data)