from odoo import models, fields, api


class ThomasMessage(models.TransientModel):

    _name = 'thomaslease.message'
    _description = 'General Messages for Thomas Leasing Operations'

    title = fields.Char('Title')
    message = fields.Html(readonly=True)
    ok_handler = False
    #invoice_ids = fields.One2many('account.invoice', 'message_id', string='Invoices')
    #lease_ids = fields.One2many('thomaslease.lease', string='Lease Agreements')

    def ok_pressed(self):
        print("OK Pressed")
        res = self.env[self.env.context['active_model']].browse(self.env.context['active_id'])
        if res:
            res.ok_pressed()

    def cancel_pressed(self):
        return
