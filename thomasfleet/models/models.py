# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging, pprint
from datetime import date

def dump_obj(obj):
    fields_dict ={}
    for key in obj.fields_get():
        fields_dict[key] = obj[key]
    return fields_dict

class ThomasFleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    log = logging.getLogger('thomas')
    log.setLevel(logging.INFO)

    #name = fields.Char(compute='_compute_vehicle_name', store=True)
    unit_no = fields.Char('Unit #', readonly=True)
    unit_slug = fields.Char(compute='_compute_slug', readonly=True)
    vin_id = fields.Char('V.I.N')
    license_plate = fields.Char('License Plate', required=False)
    trim_id = fields.Many2one('thomasfleet.trim', 'Sub Model', help='Trim for the Model of the vehicle',
                              domain="[('model_id','=',model_id)]")
    location = fields.Many2one('thomasfleet.location')
    #fields.Selection([('hamilton', 'Hamilton'), ('selkirk', 'Selkirk'), ('niagara', 'Niagara')])
    notes = fields.Text('Notes')
    door_access_code= fields.Char('Door Access Code')
    body_style = fields.Char('Body Style')
    drive = fields.Char('Drive')
    wheel_studs = fields.Integer('Wheel Studs')
    wheel_base = fields.Float('Wheel Base')
    box_size = fields.Float('Box Size')
    seat_material= fields.Many2one('thomasfleet.seatmaterial' , 'Seat Material')
    flooring = fields.Many2one('thomasfleet.floormaterial' ,'Floor Material')
    trailer_hitch = fields.Selection([('yes', 'Yes'), ('no', 'No')],'Trailer Hitch', default='yes')
    brake_controller = fields.Selection([('yes', 'Yes'), ('no', 'No')],'Brake Controller', default='yes')
    tires= fields.Char('Tires')
    capless_fuel_filler =fields.Selection([('yes', 'Yes'), ('no', 'No')],'Capless Fuel Filler', default='no')
    bluetooth = fields.Selection([('yes', 'Yes'), ('no', 'No')],'Bluetooth', default='yes')
    navigation = fields.Selection([('yes', 'Yes'), ('no', 'No')],'Navigation', default='no')
    warranty_start_date = fields.Date('Warranty Start Date')
    seat_belts = fields.Integer('# Seat Belts')
    seats = fields.Integer('# Seats', help='Number of seats of the vehicle')
    doors = fields.Integer('# Doors', help='Number of doors of the vehicle', default=5)
   # fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel')],'Fuel Type', default='gasoline')
    charge_code = fields.Char('Charge Code')
    rim = fields.Char('Rim')
    engine = fields.Char('Engine')
    fuel_type =  fields.Many2one('thomasfleet.fueltype', 'Fuel Type' )
    def notes_compute(self):
        self.log.info('Computing Notes')
        for record in self:
            record.notes ='here are the core notesnotes'

    @api.depends('unit_no', 'model_id')
    def _compute_slug(self):
        for record in self:
            if record.unit_no and record.model_id:
                record.unit_slug = 'Unit # - ' + record.unit_no + '-' + record.model_id.brand_id.name + '/' + record.model_id.name
            else:
                record.unit_slug = 'Unit # - '
   # @api.depends('create_date')
   # def compute_unit_no(self):
   #      self.log.info('Here I am')
   #      for record in self:
   #          last_vehicle = self.env['fleet.vehicle'].search([], limit=1, order='create_date desc')
   #          self.log.info('last Vehicle date %s', last_vehicle.name)
   #          self.log.info('last Vehicle unit # %s', last_vehicle.unit_no)
   #          if last_vehicle:
   #             record.unit_no = last_vehicle.unit_no + 1
   #          else:
   #             record.unit_no = record.create_date.year

    @api.model
    def create(self, data):
        self.log.info('CREATING THIS THING')
        last_vehicle =self.env['fleet.vehicle'].search([], limit=1, order='create_date desc')
        self.log.info('last Vehicle Name %s', last_vehicle.name)
        #self.log.info('last Vehicle Name %s',  fields.Datetime.to_string(last_vehicle.create_date))
        attr = vars(last_vehicle)
        self.log.info(dump_obj(last_vehicle))
        record = super(ThomasFleetVehicle,self).create(data)
        #record.notes =dump_obj(last_vehicle)
        right_now_yr = int(date.today().strftime('%y'))
        #self.log.info('Curent Yr %d', right_now_yr)
        if last_vehicle.unit_no:
            cur_unit_no_yr=int(last_vehicle.unit_no[0:2])
            #self.log.info('Unit Yr %d', cur_unit_no_yr)
            if right_now_yr - cur_unit_no_yr == 0:
                record.unit_no = str(int(last_vehicle.unit_no)+1)
            else:
                record.unit_no = str(right_now_yr * 100 )
        else:
            record.unit_no =str(right_now_yr * 100 )

        return record

class ThomasFleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    trim_id = fields.One2many('thomasfleet.trim', 'model_id', 'Available Trims')


class ThomasFleetTrim(models.Model):
    _name = 'thomasfleet.trim'

    name = fields.Char('Trim Name')
    description = fields.Char('Description')
    model_id = fields.Many2one('fleet.vehicle.model', 'Model' 'Available Trims')
    model_name = fields.Char(related='model_id.name')
    make_name = fields.Char(related='model_id.brand_id.name')

class ThomasFleetLocation(models.Model):
    _name = 'thomasfleet.location'

    name = fields.Char('Location')
    description = fields.Char('Description')

class ThomasFleetSeatMaterial(models.Model):
    _name = 'thomasfleet.seatmaterial'

    name = fields.Char('Seat Material')
    description = fields.Char('Description')


class ThomasFleetFloorMaterial(models.Model):
    _name = 'thomasfleet.floormaterial'
    name = fields.Char('Floor Material')
    description = fields.Char('Description')

class ThomasFleetFuelType(models.Model):
    _name = 'thomasfleet.fueltype'

    name = fields.Char('Fuel Type')
    description = fields.Char('Description')

    #     name = fields.Char()
    #     value = fields.Integer()
    #     value2 = fields.Float(compute="_value_pc", store=True)
    #     description = fields.Text()
    #
    #     @api.depends('value')
    #     def _value_pc(self):
    #         self.value2 = float(self.value) / 100
