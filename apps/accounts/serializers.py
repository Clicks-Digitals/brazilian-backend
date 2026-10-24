from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from rest_framework import serializers

from apps.accounts.models import AdminRole, CustomerAddress, Permission, User


class UserPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "user_type",
            "marketing_opt_in",
            "loyalty_consent",
            "is_staff",
            "is_superuser",
            "role",
            "role_name",
            "permissions",
        )
        read_only_fields = fields

    def get_permissions(self, obj):
        if obj.is_superuser:
            return list(Permission.objects.values_list("code", flat=True))
        if not obj.role_id:
            return []
        return list(obj.role.permissions.values_list("code", flat=True))


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    marketing_opt_in = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value


class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "marketing_opt_in",
            "loyalty_consent",
        )
        read_only_fields = ("id", "email")


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = (
            "id",
            "label",
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "area",
            "country",
            "delivery_instructions",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "code", "module", "action", "description")


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        many=True, slug_field="code", queryset=Permission.objects.all(), required=False
    )
    permission_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = AdminRole
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "is_system",
            "permissions",
            "permission_codes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_slug(self, value):
        return slugify(value) if value else value

    def create(self, validated_data):
        codes = validated_data.pop("permission_codes", None)
        permissions = validated_data.pop("permissions", [])
        role = AdminRole.objects.create(**validated_data)
        if codes is not None:
            permissions = list(Permission.objects.filter(code__in=codes))
        if permissions:
            role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        codes = validated_data.pop("permission_codes", None)
        permissions = validated_data.pop("permissions", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if codes is not None:
            instance.permissions.set(Permission.objects.filter(code__in=codes))
        elif permissions is not None:
            instance.permissions.set(permissions)
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    full_name = serializers.CharField(read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "user_type",
            "role",
            "role_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "permissions",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined", "is_superuser")

    def get_permissions(self, obj):
        if obj.is_superuser:
            return list(Permission.objects.values_list("code", flat=True))
        if not obj.role_id:
            return []
        return list(obj.role.permissions.values_list("code", flat=True))

    def validate_email(self, value):
        return User.objects.normalize_email(value).lower()

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        validated_data.setdefault("user_type", User.UserType.STAFF)
        validated_data.setdefault("is_staff", True)
        user = User.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class AdminCustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    notes_internal = serializers.CharField(
        source="profile.notes_internal", required=False, allow_blank=True
    )
    order_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(
        max_digits=12, decimal_places=3, read_only=True, coerce_to_string=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "is_active",
            "marketing_opt_in",
            "notes_internal",
            "order_count",
            "total_spent",
            "date_joined",
        )
        read_only_fields = (
            "id",
            "email",
            "order_count",
            "total_spent",
            "date_joined",
            "full_name",
        )

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if profile_data is not None:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        return instance
