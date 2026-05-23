import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _classify_role(user, Shop):
    owns_shop = Shop.objects.filter(manager_id=user.pk).exists()
    has_branch_access = (
        user.allowed_branches.exists()
        or user.managed_shops_all_branches.exists()
        or user.created_for_shop_id is not None
    )
    if owns_shop or (getattr(user, "can_create_shop", False) and not has_branch_access):
        return "shop_manager"
    if not getattr(user, "can_create_shop", True) or has_branch_access:
        return "branch_manager"
    return "end_user"


def _insert_or_replace_created_for_shop(cursor, vendor: str) -> None:
    if vendor == "postgresql":
        cursor.execute(
            """
            INSERT INTO _migration_user_created_for_shop (user_id, created_for_shop_id)
            SELECT id, created_for_shop_id
            FROM module_account_user
            WHERE created_for_shop_id IS NOT NULL
            ON CONFLICT (user_id) DO UPDATE
            SET created_for_shop_id = EXCLUDED.created_for_shop_id
            """
        )
        return
    cursor.execute(
        """
        INSERT OR REPLACE INTO _migration_user_created_for_shop (user_id, created_for_shop_id)
        SELECT id, created_for_shop_id
        FROM module_account_user
        WHERE created_for_shop_id IS NOT NULL
        """
    )


def _insert_ignore(cursor, vendor: str, sql_sqlite: str, sql_postgres: str) -> None:
    cursor.execute(sql_postgres if vendor == "postgresql" else sql_sqlite)


def backup_branch_staff_data(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS _migration_user_created_for_shop (
                user_id INTEGER PRIMARY KEY,
                created_for_shop_id INTEGER
            )
            """
        )
        _insert_or_replace_created_for_shop(cursor, vendor)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS _migration_user_allowed_branches (
                user_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, branch_id)
            )
            """
        )
        _insert_ignore(
            cursor,
            vendor,
            """
            INSERT OR IGNORE INTO _migration_user_allowed_branches (user_id, branch_id)
            SELECT user_id, branch_id FROM module_account_user_allowed_branches
            """,
            """
            INSERT INTO _migration_user_allowed_branches (user_id, branch_id)
            SELECT user_id, branch_id FROM module_account_user_allowed_branches
            ON CONFLICT DO NOTHING
            """,
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS _migration_user_managed_shops_all (
                user_id INTEGER NOT NULL,
                shop_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, shop_id)
            )
            """
        )
        _insert_ignore(
            cursor,
            vendor,
            """
            INSERT OR IGNORE INTO _migration_user_managed_shops_all (user_id, shop_id)
            SELECT user_id, shop_id FROM module_account_user_managed_shops_all_branches
            """,
            """
            INSERT INTO _migration_user_managed_shops_all (user_id, shop_id)
            SELECT user_id, shop_id FROM module_account_user_managed_shops_all_branches
            ON CONFLICT DO NOTHING
            """,
        )


def assign_roles(apps, schema_editor):
    User = apps.get_model("module_account", "User")
    Shop = apps.get_model("module_shop", "Shop")
    for user in User.objects.all().iterator():
        if user.is_superuser or user.is_staff:
            role = "shop_manager"
        else:
            role = _classify_role(user, Shop)
        User.objects.filter(pk=user.pk).update(role=role)


def create_profiles_and_restore(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor

    with connection.cursor() as cursor:
        _insert_ignore(
            cursor,
            vendor,
            """
            INSERT OR IGNORE INTO module_account_shopmanager (user_ptr_id)
            SELECT id FROM module_account_user WHERE role = 'shop_manager'
            """,
            """
            INSERT INTO module_account_shopmanager (user_ptr_id)
            SELECT id FROM module_account_user WHERE role = 'shop_manager'
            ON CONFLICT DO NOTHING
            """,
        )
        _insert_ignore(
            cursor,
            vendor,
            """
            INSERT OR IGNORE INTO module_account_branchmanager (user_ptr_id)
            SELECT id FROM module_account_user WHERE role = 'branch_manager'
            """,
            """
            INSERT INTO module_account_branchmanager (user_ptr_id)
            SELECT id FROM module_account_user WHERE role = 'branch_manager'
            ON CONFLICT DO NOTHING
            """,
        )
        _insert_ignore(
            cursor,
            vendor,
            """
            INSERT OR IGNORE INTO module_account_enduser (user_ptr_id)
            SELECT id FROM module_account_user WHERE role = 'end_user'
            """,
            """
            INSERT INTO module_account_enduser (user_ptr_id)
            SELECT id FROM module_account_user WHERE role = 'end_user'
            ON CONFLICT DO NOTHING
            """,
        )
        cursor.execute(
            """
            UPDATE module_account_branchmanager
            SET created_for_shop_id = (
                SELECT created_for_shop_id
                FROM _migration_user_created_for_shop
                WHERE user_id = module_account_branchmanager.user_ptr_id
            )
            WHERE user_ptr_id IN (SELECT user_id FROM _migration_user_created_for_shop)
            """
        )
        _insert_ignore(
            cursor,
            vendor,
            """
            INSERT OR IGNORE INTO module_account_branchmanager_allowed_branches (branchmanager_id, branch_id)
            SELECT b.user_id, b.branch_id
            FROM _migration_user_allowed_branches b
            INNER JOIN module_account_user u ON u.id = b.user_id AND u.role = 'branch_manager'
            """,
            """
            INSERT INTO module_account_branchmanager_allowed_branches (branchmanager_id, branch_id)
            SELECT b.user_id, b.branch_id
            FROM _migration_user_allowed_branches b
            INNER JOIN module_account_user u ON u.id = b.user_id AND u.role = 'branch_manager'
            ON CONFLICT DO NOTHING
            """,
        )
        _insert_ignore(
            cursor,
            vendor,
            """
            INSERT OR IGNORE INTO module_account_branchmanager_managed_shops_all_branches (branchmanager_id, shop_id)
            SELECT m.user_id, m.shop_id
            FROM _migration_user_managed_shops_all m
            INNER JOIN module_account_user u ON u.id = m.user_id AND u.role = 'branch_manager'
            """,
            """
            INSERT INTO module_account_branchmanager_managed_shops_all_branches (branchmanager_id, shop_id)
            SELECT m.user_id, m.shop_id
            FROM _migration_user_managed_shops_all m
            INNER JOIN module_account_user u ON u.id = m.user_id AND u.role = 'branch_manager'
            ON CONFLICT DO NOTHING
            """,
        )
        cursor.execute("DROP TABLE IF EXISTS _migration_user_created_for_shop")
        cursor.execute("DROP TABLE IF EXISTS _migration_user_allowed_branches")
        cursor.execute("DROP TABLE IF EXISTS _migration_user_managed_shops_all")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("module_account", "0005_alter_user_phone_number_and_more"),
        ("module_shop", "0002_rename_shop_owner_to_manager"),
        ("module_product", "0003_alter_product_branch_specialoffertransaction_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("shop_manager", "Shop manager"),
                    ("branch_manager", "Branch manager"),
                    ("end_user", "End user"),
                ],
                db_index=True,
                default="branch_manager",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(backup_branch_staff_data, noop_reverse),
        migrations.RunPython(assign_roles, noop_reverse),
        migrations.RemoveField(
            model_name="user",
            name="allowed_branches",
        ),
        migrations.RemoveField(
            model_name="user",
            name="managed_shops_all_branches",
        ),
        migrations.RemoveField(
            model_name="user",
            name="created_for_shop",
        ),
        migrations.RemoveField(
            model_name="user",
            name="can_create_shop",
        ),
        migrations.CreateModel(
            name="ShopManager",
            fields=[
                (
                    "user_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "shop manager",
                "verbose_name_plural": "shop managers",
            },
            bases=("module_account.user",),
        ),
        migrations.CreateModel(
            name="EndUser",
            fields=[
                (
                    "user_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "end user",
                "verbose_name_plural": "end users",
            },
            bases=("module_account.user",),
        ),
        migrations.CreateModel(
            name="BranchManager",
            fields=[
                (
                    "user_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_for_shop",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="staff_invited_for_shop",
                        to="module_shop.shop",
                    ),
                ),
                (
                    "allowed_branches",
                    models.ManyToManyField(
                        blank=True,
                        related_name="allowed_users",
                        to="module_shop.branch",
                    ),
                ),
                (
                    "managed_shops_all_branches",
                    models.ManyToManyField(
                        blank=True,
                        related_name="all_branch_managers",
                        to="module_shop.shop",
                    ),
                ),
            ],
            options={
                "verbose_name": "branch manager",
                "verbose_name_plural": "branch managers",
            },
            bases=("module_account.user",),
        ),
        migrations.RunPython(create_profiles_and_restore, noop_reverse),
    ]
