from google.appengine.ext import ndb

class Foto(ndb.Model):
    titulo = ndb.StringProperty(required=True)
    autor = ndb.StringProperty(required=True)
    pic = ndb.BlobKeyProperty(required=True)
    mod = ndb.BlobKeyProperty()
    fecha_creacion = ndb.DateProperty()

class Usuario(ndb.Model):
    correo = ndb.StringProperty (required=True)
    nombre = ndb.StringProperty ()
    passwd = ndb.StringProperty (required=True)