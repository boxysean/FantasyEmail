import models
from django.contrib import admin

class EmailerAdmin(admin.ModelAdmin):
	list_display = ("name", "user")
	list_display_links = ("name", "user")
	ordering = ("name", "user")

admin.site.register(models.Emailer, EmailerAdmin)



class EmailAddressAdmin(admin.ModelAdmin):
	list_display = ("emailer", "emailAddress")
	ordering = ("emailer",)
	search_fields = ("emailer", "emailAddress")

admin.site.register(models.EmailAddress, EmailAddressAdmin)

# 
# 
# class UserAdmin(admin.ModelAdmin):
# 	list_display = ("name",)
# 	ordering = ("name",)
# 	search_fields = ("name",)
# 
# admin.site.register(models.User, UserAdmin)
# 


class TeamAdmin(admin.ModelAdmin):
	list_display = ("user", "name", "icon")
	ordering = ("user",)
	search_fields = ("user",)

admin.site.register(models.Team, TeamAdmin)



class PlayerAdmin(admin.ModelAdmin):
	list_display = ("emailer", "team")
	list_filter = ("team",)
	ordering = ("team", "emailer")
	search = ("team", "emailer")

admin.site.register(models.Player, PlayerAdmin)



class PlayerTransactionAdmin(admin.ModelAdmin):
	list_display = ("emailer", "team", "timestamp", "add")
	list_filter = ("team",)
	ordering = ("-timestamp",)
	search = ("team", "emailer")

admin.site.register(models.PlayerTransaction, PlayerTransactionAdmin)



class CategoryAdmin(admin.ModelAdmin):
	list_display = ("name",)

admin.site.register(models.Category, CategoryAdmin)



class EmailerStatsAdmin(admin.ModelAdmin):
	list_display = ("emailer", "category", "stat")
	list_filter = ("emailer", "category")
	ordering = ("emailer", "category")
	search = ("emailer", "category")

admin.site.register(models.EmailerStats, EmailerStatsAdmin)



class EmailerStatsHistoryAdmin(admin.ModelAdmin):
	list_display = ("timestamp", "emailer", "category", "stat")
	list_filter = ("timestamp", "emailer", "category")
	ordering = ("timestamp", "emailer", "category")
	search = ("timestamp", "emailer", "category")

admin.site.register(models.EmailerStatsHistory, EmailerStatsHistoryAdmin)



class TeamPointsAdmin(admin.ModelAdmin):
	list_display = ("team", "category", "points")
	list_filter = ("team", "category")
	ordering = ("team", "category")
	search = ("team", "category")

admin.site.register(models.TeamPoints, TeamPointsAdmin)



class TeamStatsHistoryAdmin(admin.ModelAdmin):
	list_display = ("timestamp", "team", "category", "stat")
	list_filter = ("timestamp", "team", "category")
	ordering = ("timestamp", "team", "category")
	search = ("timestamp", "team", "category")

admin.site.register(models.TeamStatsHistory, TeamStatsHistoryAdmin)



class TeamStatsAdmin(admin.ModelAdmin):
	list_display = ("team", "category", "stat")
	list_filter = ("team", "category")
	ordering = ("team", "category")
	search = ("team", "category")

admin.site.register(models.TeamStats, TeamStatsAdmin)



class EmailAdmin(admin.ModelAdmin):
	list_display = ("timestamp", "emailer", "subject")

admin.site.register(models.Email, EmailAdmin)


class EmailPointAdmin(admin.ModelAdmin):
	list_display = ("email", "category", "awardTo", "points")
	list_filter = ("category",)

admin.site.register(models.EmailPoint, EmailPointAdmin)




