from odoo import models, fields, api


class ThomasMessage(models.TransientModel):

    _name = 'thomaslease.message'
    _description = 'General Messages for Thomas Leasing Operations'

    title = fields.Char('Title')
    message = fields.Html(readonly=True)
    #invoice_ids = fields.One2many('account.invoice', 'message_id', string='Invoices')
    #lease_ids = fields.One2many('thomaslease.lease', string='Lease Agreements')