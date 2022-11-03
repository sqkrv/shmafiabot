from peewee import SqliteDatabase, Model, TextField, PrimaryKeyField, ForeignKeyField, BooleanField

db = SqliteDatabase("shmafiabot.db")


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    user_id = PrimaryKeyField()
    username = TextField(unique=True)
    first_name = TextField()
    last_name = TextField()
    bot = BooleanField(null=False, default=False)
    member = BooleanField(null=False, default=True)


class MentionGroup(BaseModel):
    id = PrimaryKeyField()
    name = TextField(null=False)

    class Meta:
        table_name = "mention_group"


class GroupAffiliation(BaseModel):
    # id = PrimaryKeyField()
    mention_group_id = ForeignKeyField(MentionGroup, 'id')
    user_id = ForeignKeyField(User, 'user_id')

    class Meta:
        table_name = "group_affiliation"


class RestrictedUser(BaseModel):
    id = PrimaryKeyField()
    user_id = ForeignKeyField(User, 'user_id', null=False)

    class Meta:
        table_name = "restricted_user"
