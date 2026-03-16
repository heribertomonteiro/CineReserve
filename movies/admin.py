from django.contrib import admin

from movies.models import Movie

# Register your models here.
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'release_date', 'duration')
    search_fields = ('title',)
    list_filter = ('release_date',)