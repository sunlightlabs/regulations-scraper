from doc import Doc, Attachment, View, DOC_TYPES
from docket import Docket
from agency import Agency
from entity import Entity

from mongoengine import connect
from settings import DB_NAME, DB_SETTINGS
connect(DB_NAME, **DB_SETTINGS)