# Create file: module_shop/admin_mixins.py
from django.core.cache import cache
from django.db.models import Count, Q

class CachedAdminMixin:
    """Add caching for expensive admin queries"""
    
    def get_cached_queryset(self, request, cache_key, queryset_func, timeout=300):
        cache_key = f"admin_{cache_key}_{request.user.id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        result = queryset_func()
        cache.set(cache_key, result, timeout)
        return result