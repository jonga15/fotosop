#!/usr/bin/env python
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import urllib
import datetime
import re
import base64
import logging
import Image

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images
from numpy import array
from google.appengine.api import files



import webapp2
import jinja2
from clases import *

JINJA_ENVIRONMENT = jinja2.Environment(
                                       loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)
NOMBRE = ""
CORREO = ""

class Inicio(webapp2.RequestHandler):
    
    def get(self):
        fotos = Foto.query() # por comprobar
        fotos.fetch(limit = 50)
        template_values = {'fotos' : fotos}
        template = JINJA_ENVIRONMENT.get_template('html/inicio.html')
        self.response.write(template.render(template_values))

class IniciarSesion(webapp2.RequestHandler):
    
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('html/inicioSesion.html')
        self.response.write(template.render(template_values))

    def post(self):
        error = False
        contrasena = self.request.get('passwd')
        email = self.request.get('email')
        try:
            userT = Usuario.query(Usuario.correo == email).get()
            passDecodificada = base64.decodestring(userT.passwd)
            if passDecodificada != contrasena:
                error = True
        except: 
            error = True
            pass
        if error:
            template_values = {
                'mensaje_error' : "No se ha podido llevar a cabo el inicio de sesion",
                'email' : email
            }
            template = JINJA_ENVIRONMENT.get_template('html/inicioSesion.html')
            self.response.write(template.render(template_values))
        else:
            global CORREO
            CORREO = email
            global NOMBRE
            NOMBRE = userT.nombre
            self.redirect('/inicioUsuario')
class Registro(webapp2.RequestHandler):

    def get(self):
        id = self.request.get('id')
                                    
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('html/registro.html')
        self.response.write(template.render(template_values))
    
    def post(self):
        validar_error = ""
        email_error = ""
        passwd_error = ""
        
        PASSWORD_RE = re.compile(r"^.{3,20}$")
        EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
        
        def valid_password(passwd):
            return PASSWORD_RE.match(passwd)
        
        def valid_email(correo):
            return EMAIL_RE.match(correo)
        
        contr1 = self.request.get('passwd1')
        contr2 = self.request.get('passwd2')
        correo= self.request.get('email')
        nombre=self.request.get('nombre')
        
        userT = Usuario.query(Usuario.correo == correo).get()

        error = False
        if userT is not None:
            email_error = "El usuario ya existe"
        if not valid_email(correo):
            email_error = "Email invalido"
            error = True
        if correo is None:
            email_error = "Campo requerido"
            error = True
        if not valid_password(contr1):
            passwd_error = "Password invalida"
            error = True
        if contr1 is None:
            passwd_error = "Campo requerido"
            error = True
        if contr1 != contr2:
            validar_error = "los password no coinciden"
            error = True
        if error:
            template_values = {
                'email' : correo,
                'nombre' : nombre,
                'validar_error' : validar_error,
                'email_error' : email_error,
                'passwd_error' : passwd_error,
            }
            template = JINJA_ENVIRONMENT.get_template('html/registro.html')
            self.response.write(template.render(template_values))
        else:
            contr1 = base64.encodestring(contr1)
            self.usuario = Usuario(correo = correo,
                                   nombre = nombre,
                                   passwd = contr1,
                                   )
            global NOMBRE
            NOMBRE = nombre
            global CORREO
            CORREO = correo
            self.usuario.put()
            self.redirect('/inicioUsuario')

class SubirFoto (blobstore_handlers.BlobstoreUploadHandler):

    def get(self):
        global CORREO
        global NOMBRE
        if NOMBRE=="" or CORREO=="":
            self.redirect('/')
        upload_url = blobstore.create_upload_url('/subir')
        template_values = {'url' : upload_url,}
        template = JINJA_ENVIRONMENT.get_template('html/subir.html')
        self.response.write(template.render(template_values))

    def post(self):

        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        global NOMBRE
        date = datetime.datetime.now()
        titulo= self.request.get('title')
        pic = self.request.get('pic')
        #crear una copia de la imagen para que se pueda modificar
        img = images.Image(blob_key=blob_info.key())
        img.rotate(360)
        thumbnail = img.execute_transforms(output_encoding=images.JPEG)
        file_name = files.blobstore.create(mime_type='image/jpeg', _blobinfo_uploaded_filename="copia")
        with files.open(file_name, 'a') as f:
          f.write(thumbnail)
        files.finalize(file_name)
        #almacenar objeto foto
        self.foto = Foto(titulo = titulo,
                            autor = NOMBRE,
                            pic = blob_info.key(),
                            mod = files.blobstore.get_blob_key(file_name),                              
                            fecha_creacion = date,
                            )
        self.foto.put()
        self.redirect('/inicioUsuario')

class ServeHandler (blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(resource)

class InicioUsuario(blobstore_handlers.BlobstoreDownloadHandler):
    
    def get(self):
        global CORREO
        global NOMBRE
        if NOMBRE=="" or CORREO=="":
            self.redirect('/')
        fotos = Foto.query(Foto.autor == NOMBRE)
        album = fotos.fetch(limit=50)
        template_values = {'fotos' : album,
                            'usuario' : NOMBRE,
                            }
        template = JINJA_ENVIRONMENT.get_template('html/inicioUsuario.html')
        self.response.write(template.render(template_values))

class Editar(blobstore_handlers.BlobstoreDownloadHandler):

    def get(self, resource):
        global CORREO
        global NOMBRE
        if NOMBRE=="" or CORREO=="":
            self.redirect('/')
        bk = blobstore.BlobKey(resource)
        foto = Foto.query(Foto.pic == bk).get()
        template_values = {'url' : resource,
                            'foto' : foto,
                            }
        template = JINJA_ENVIRONMENT.get_template('html/editar.html')
        self.response.write(template.render(template_values))

    def post(self, resource):
        bk = blobstore.BlobKey(resource)
        img = images.Image(blob_key=bk)

        """arr = array(img)

        for i in range(arr.shape[0]):
                for j in range(arr.shape[1]):
                    arr[i,j,0] = 0

        img = Image.fromarray(arr)
        """

        if self.request.get("resize")=="resize":
            img.resize(int(self.request.get("rx")), int(self.request.get("ry")))
        if self.request.get("rotate")=="rotate":
            img.rotate(int(self.request.get("degree"))*90)
        if self.request.get("fliph")=="fliph":
            img.horizontal_flip()
        if self.request.get("flipv")=="flipv":
            img.vertical_flip()
        if self.request.get("lucky")=="lucky":
            img.im_feeling_lucky()
        thumbnail = img.execute_transforms(output_encoding=images.JPEG)

        foto = Foto.query(Foto.mod == bk).get()
        # Remove the previous mod
        blobstore.delete(foto.mod)

        # Save Resized Image back to blobstore
        file_name = files.blobstore.create(mime_type='image/jpeg')
        with files.open(file_name, 'a') as f:
          f.write(thumbnail)
        files.finalize(file_name)
        # Save mod's blobkey
        foto.mod = files.blobstore.get_blob_key(file_name)
        foto.put()


        template_values = {'url' : str(foto.pic),
                            'foto' : foto,
                            }
        template = JINJA_ENVIRONMENT.get_template('html/editar.html')
        self.response.write(template.render(template_values))

class CerrarSesion (webapp2.RequestHandler):
    def get(self):
        global NOMBRE
        NOMBRE = ""
        global CORREO
        CORREO = ""
        self.redirect('/')

app = webapp2.WSGIApplication([
    ('/', Inicio),
    ('/inicioSesion', IniciarSesion),
    ('/registro', Registro),
    ('/cerrarSesion' , CerrarSesion),
    ('/inicioUsuario', InicioUsuario),
    ('/subir', SubirFoto),
    ('/serve/([^/]+)?', ServeHandler),
    ('/editar/([^/]+)?', Editar),
], debug=True)