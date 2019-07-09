# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests, json, uuid, jsonpath
from urllib import parse

class ThomasAccountingInvoice(models.Model):

    _inherit = 'account.invoice'

    #department = fields.Char(string='Department')
    qc_check = fields.Boolean(string='Data Accuracy Validation')
    invoice_type = fields.Selection([('lease','Lease'),('maintenance', 'Maintenance')])
    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #")

