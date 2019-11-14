from odoo import models, fields, api


class ThomasProduct(models.Model):

    _inherit = 'product.template'


    rate_type = fields.Selection([('monthly', 'Monthly'),
                                  ('weekly', 'Weekly'),
                                  ('daily', 'Daily'),
                                  ('biweekly', 'Bi-Weekly'),
                                  ('term', 'Term'),
                                  ('amd_daily_pu', 'AMD Daily Pickup'),
                                  ('amd_daily_cc', 'AMD Daily Crew Cab'),
                                  ('amd_daily_ts', 'AMD Daily Tandem Stake'),
                                  ('amd_daily_tr', 'AMD Daily Tractor'),
                                  ('amd_daily_ft', 'AMD Daily Flat Truck'),
                                  ('stelco_daily','Stelco Daily'),
                                  ('stelco_weekly','Stelco Weekly'),
                                  ('stelco_monthly','Stelco Monthly')
                                  ],
                                 'Rate Type', default='monthly',
                                 track_visibility='onchange')

