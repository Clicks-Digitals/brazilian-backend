from django.contrib import admin

from apps.accounts.models import AdminRole, CustomerAddress, CustomerProfile, Permission, User


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    extra = 0


class AddressInline(admin.TabularInline):
    model = CustomerAddress
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "user_type", "role", "is_staff", "is_active")
    list_filter = ("user_type", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name", "phone")
    inlines = [CustomerProfileInline, AddressInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "module", "action")
    search_fields = ("code",)


@admin.register(AdminRole)
class AdminRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_system")
    filter_horizontal = ("permissions",)


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "city", "is_default")
    search_fields = ("full_name", "user__email", "city")
