# -*- coding: utf-8 -*-

""" Upload data to APIs """

import os
import shutil
import subprocess as shell
from flask import request, send_from_directory
from werkzeug import secure_filename
from ... import htmlcodes as hcodes
from ..base import ExtendedApiResource
from ... import get_logger

UPLOAD_FOLDER = '/uploads'
INTERPRETER = 'python'
ZBIN = '/zoomify/processor/ZoomifyFileProcessor.py'
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

logger = get_logger(__name__)


# Save files http://API/upload
class Uploader(ExtendedApiResource):

    allowed_exts = ['png', 'jpg', 'jpeg', 'tiff']

    def allowed_file(self, filename):
        return '.' in filename \
            and filename.rsplit('.', 1)[1].lower() in self.allowed_exts

    def post(self):

        if 'file' not in request.files:
            return "No files specified"

        myfile = request.files['file']

        if not self.allowed_file(myfile.filename):
            return "File extension not allowed", hcodes.HTTP_BAD_REQUEST

        # Check file name
        filename = secure_filename(myfile.filename)
        abs_file = os.path.join(UPLOAD_FOLDER, filename)
        logger.info("File request for [%s](%s)" % (myfile, abs_file))

        if os.path.exists(abs_file):
            # os.remove(abs_file) # ??
            logger.warn("Already exists")
            return "File '" + filename + "' already exists. Please " + \
                "change its name and retry.", hcodes.HTTP_BAD_REQUEST

        # Save the file
        try:
            myfile.save(abs_file)
        except Exception:
            return "Failed to save file", hcodes.HTTP_DEFAULT_SERVICE_FAIL

#             # Make zoomify object and thumbnail
#             app.logger.info("Elaborate image")
#             # Proc via current shell
#             cmd = [INTERPRETER, ZBIN, abs_file]
#             proc = shell.Popen(cmd, stdout=shell.PIPE, stderr=shell.PIPE)
#             out, err = proc.communicate()
#             # Handle output
#             if proc.returncode == 0:
#                 if out != None and out != "":
#                     app.logger.info("Comm output: " + out)
#             else:
#                 app.logger.critical("Failed to process image " + abs_file + \
#                     ". Error: " + err)
#                 abort(hcodes.HTTP_BAD_REQUEST, "Could not process file")

        # Default redirect is to 302 state, which makes client
        # think that response was unauthorized....
        # see http://dotnet.dzone.com/articles/getting-know-cross-origin
        return "Uploaded", hcodes.HTTP_OK_BASIC

    def delete(self, filename):
        """ Remove the file if requested """

        abs_file = os.path.join(UPLOAD_FOLDER, filename)

        # Check file existence
        if not os.path.exists(abs_file):
            logger.critical("File '%s' not found" % abs_file)
            return "File not found", hcodes.HTTP_BAD_NOTFOUND

        return True

#         # Remove zoomified directory
#         filebase, fileext = os.path.splitext(abs_file)
#         if os.path.exists(filebase):
#             shutil.rmtree(filebase)
#             app.logger.warn("Removed: "+ filebase +" [extension '"+fileext+"']")

#         # Remove the real file
#         os.remove(abs_file)
#         app.logger.warn("Removed: "+ abs_file)

#         return "Deleted", hcodes.HTTP_OK_NORESPONSE

#     # To get?
#     elif request.method == 'GET':
#         app.logger.info("Should provide: "+ abs_file)
#         return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#     return ''' <!doctype html> <title>Uploader</title> Empty<br> '''
