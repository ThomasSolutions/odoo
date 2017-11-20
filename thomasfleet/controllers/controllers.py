# -*- coding: utf-8 -*-
from odoo import http

# class Thomasfleet(http.Controller):
#     @http.route('/thomasfleet/thomasfleet/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/thomasfleet/thomasfleet/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('thomasfleet.listing', {
#             'root': '/thomasfleet/thomasfleet',
#             'objects': http.request.env['thomasfleet.thomasfleet'].search([]),
#         })

#     @http.route('/thomasfleet/thomasfleet/objects/<model("thomasfleet.thomasfleet"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('thomasfleet.object', {
#             'object': obj
#         })