from django.contrib import admin

from . import models


class ScoreInline(admin.StackedInline):
    model= models.Score

class ShopAdmin(admin.ModelAdmin):
    inlines= (ScoreInline, )
    pass

admin.site.register(models.Shop, ShopAdmin)
admin.site.register(models.Branch)
admin.site.register(models.Score)
