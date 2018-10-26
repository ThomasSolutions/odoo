# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging, pprint,requests,json,uuid,jsonpath
from datetime import date, datetime


def dump_obj(obj):
    fields_dict = {}
    for key in obj.fields_get():
        fields_dict[key] = obj[key]
    return fields_dict


class ThomasAsset(models.Model):
    _name = 'thomas.asset'
    unit_no = fields.Char('Unit #')
    notes = fields.Text('Notes')
    charge_code = fields.Char('Charge Code')
    filed_as = fields.Char("File As")
    company_acct = fields.Char("Company Acct")
    asset_class = fields.Many2one('thomasfleet.asset_class', 'Asset Class')
    insurance_class = fields.Many2one('thomasfleet.insurance_class', 'Insurance Class')
    thomas_purchase_price = fields.Float('Thomas Purchase Price')
    purchase_date = fields.Char('Purchase Date')
    usage = fields.Char('Usage')
    disposal_year = fields.Char('Disposal Year')
    disposal_date = fields.Char('Disposal Date')
    disposal_proceeds = fields.Float('Disposal Proceeds')
    sold_to = fields.Char('Sold To')
    betterment_cost = fields.Char("Betterment Cost")
    lease_status = fields.Selection([('spare','Spare'), ('maint_req','Maintenance Required'),('road_test','Road Test'),('detail','Detail'),('reserved','Customer/Reserved'),('leased', 'Leased'), ('available','Available for Lease'),('returned_inspect','Returned waiting Inspection')], 'Lease Status')

class ThomasFleetVehicle(models.Model):
    _name = 'fleet.vehicle'
    _inherit = ['thomas.asset', 'fleet.vehicle']
    _order = "unitInt asc"

    log = logging.getLogger('thomas')
    log.setLevel(logging.INFO)

    # thomas_asset = fields.Many2one('thomas.asset', ondelete='cascade')
    # fleet_vehicle = fields.Many2one('fleet.vehicle', ondelete='cascade')
    # name = fields.Char(compute='_compute_vehicle_name', store=True)

    #plate registration?
    protractor_invoices = fields.One2many('thomasfleet.invoice','vehicle_id', 'Invoices')
    unit_slug = fields.Char(compute='_compute_slug', readonly=True)
    unitInt = fields.Integer(compute='_getInteger', store=True)
    vin_id = fields.Char('V.I.N')
    license_plate = fields.Char('License Plate', required=False)
    trim_id = fields.Many2one('thomasfleet.trim', 'Trim', help='Trim for the Model of the vehicle',
                              domain="[('model_id','=',model_id)]")
    location = fields.Many2one('thomasfleet.location')
    # fields.Selection([('hamilton', 'Hamilton'), ('selkirk', 'Selkirk'), ('niagara', 'Niagara')])
    door_access_code = fields.Char('Door Access Code')
    body_style = fields.Char('Body Style')
    drive = fields.Char('Drive')
    wheel_studs = fields.Char('Wheel Studs')
    wheel_size = fields.Char('Wheel Size')
    wheel_style = fields.Char('Wheel Style')
    wheel_base = fields.Char('Wheel Base')
    box_size = fields.Char('Box Size')
    seat_material = fields.Many2one('thomasfleet.seatmaterial', 'Seat Material')
    flooring = fields.Many2one('thomasfleet.floormaterial', 'Floor Material')
    trailer_hitch = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Trailer Hitch', default='yes')
    brake_controller = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Brake Controller', default='yes')
    tires = fields.Char('Tires')
    capless_fuel_filler = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Capless Fuel Filter', default='no')
    bluetooth = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Bluetooth', default='yes')
    navigation = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Navigation', default='no')
    warranty_start_date = fields.Char('Warranty Start Date')
    seat_belts = fields.Integer('# Seat Belts')
    seats = fields.Integer('# Seats', help='Number of seats of the vehicle')
    doors = fields.Integer('# Doors', help='Number of doors of the vehicle', default=5)
    # fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel')],'Fuel Type', default='gasoline')

    rim_bolts = fields.Char('Rim Bolts')
    engine = fields.Char('Engine')
    fuel_type = fields.Many2one('thomasfleet.fueltype', 'Fuel Type')
    fleet_status = fields.Many2one('fleet.vehicle.state', 'Fleet Status')
    air_conditioning = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Air Conditioning', default='yes')
    transmission = fields.Char("Transmission")
    protractor_guid = fields.Char(compute='protractor_guid_compute')
    stored_protractor_guid = fields.Char()#compute='get_protractor_guid')

    @api.depends('unit_no')
    def _getInteger(self):
        for rec in self:
            rec.unitInt = int(rec.unit_no)

    # accessories = fields.Many2many()
    @api.depends('stored_protractor_guid')
    def protractor_guid_compute(self):
        for record in self:
            print('Computing GUID' + str(record.stored_protractor_guid))
            if not record.stored_protractor_guid:
                guid = record.get_protractor_id()
                print('Retrieved GUID' + guid)
                record.write({'stored_protractor_guid': guid})
                record.stored_protractor_guid = guid
                record.protractor_guid = guid
            else:
                record.protractor_guid = record.stored_protractor_guid
    """
    def get_protractor_guid(self):
        for record in self:
            print('Computing GUID' + str(record.protractor_guid))
            if not record.protractor_guid:
                guid = self.get_protractor_id()
                #record.protractor_guid = guid
                record.stored_protractor_guid =guid
                record.write({'protractor_guid': guid})
                #record.update({'protractor_guid': guid})
                vals = dict(record._cache)
                record.onchange({'protractor_guid': guid, 'stored_protractor_guid': guid},['stored_protractor_guid'],record._onchange_spec())
    """
    def notes_compute(self):
        self.log.info('Computing Notes')
        for record in self:
            record.notes = 'here are the core notesnotes'

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

    def update_protractor(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/a70c552f-5555-4a57-b4ea-8dbb798e7013"
        vin = self.vin_id
        plateReg = "ON"
        unit = self.unit_no
        #self.protractor_guid
        theUnit = {
            "VIN":self.vin_id,
            "PlateRegistration":"ON",
            "ID":"a70c552f-5555-4a57-b4ea-8dbb798e7013",
            "IsComplete":True,
            "Unit":self.unit_no,
            "Color": self.color,
            "Year": self.model_year,
            "Make": self.model_id.brand_id.name,
            "Model": self.model_id.name,
            "Submodel":self.trim_id.name,
            "Engine": self.engine,
            "Type":"Vehicle",
            "Lookup":self.license_plate,
            "Description": self.unit_slug,
            "Usage": 0,
            "ProductionDate":"",
            "Note":"",
            "NoEmail": False,
            "NoPostCard": False,
            "PreferredContactMethod":"Email",
            "MarketingSource":""
            }

        payload =json.dumps(theUnit)
        print(payload)
            #"{\"IsComplete\": true,\"PlateRegistration\": \""+plateReg+"\",
        # \"VIN\": \"2C4RDGBGXDR542491\",\"Unit\": \"\",\"Color\": \"PURPLE\",
        # \"Year\": 2013,\"Make\": \"Dodge\",\"Model\": \"Grand Caravan\",
        # \"Submodel\": \"SE\",\"Engine\": \"V6 3.6L 3604CC 220CID\",\"ID\":
        # \"a70c552f-5555-4a57-b4ea-8dbb798e7013\",\"Type\": \"Vehicle\",
        # \"Lookup\": \"BRDA497\",\"Description\": \"2013 Dodge Grand Caravan SE\",
        # \"Usage\": 0,\"ProductionDate\": \"0001-01-01T00:00:00\",\"Note\": \"\",
        # \"NoEmail\": false,\"NoPostCard\": false,\"PreferredContactMethod\": \"Email\",\"MarketingSource\":\"\"}"
        headers = {
            'connectionId': "de8b3762edfd41fdbc37ddc3ef4d0f1d",
            'apiKey': "3d326387107942f0bf5fa9ec342e4989",
            'authentication': "5NmTG0A6uNLnTiVcp1FZL9is+js=",
            'Accept': "application/json",
            'Content-Type': "application/json",
            'Cache-Control': "no-cache",
            'Postman-Token': "2e5fe1e2-b08e-41b8-aab1-58b75642351a"
        }

        response = requests.request("POST", url, data=payload, headers=headers)

        print(response.text)

    def get_protractor_id(self):

        self.log.info("Getting Protarctor ID for Vehicle: "+ str(self.name))

        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/"+self.vin_id

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'Cache-Control': "no-cache",
            'Postman-Token': "9caffd55-2bac-4e79-abfc-7fd1a3e84c6d"
        }

        response = requests.request("GET", url, headers=headers)

        logging.info(response.text)


        data = response.json()
        #print(data)
        return (data['ItemCollection'][0]['ID'])

    @api.multi
    def write(self, values):
        ThomasFleetVehicle_write = super(ThomasFleetVehicle,self).write(values)
        #self.update_protractor()
        #ThomasFleetVehicle_write.get_protractor_id()
        return ThomasFleetVehicle_write



    @api.model
    def create(self, data):
        self.log.info('CREATING THIS THING')
        last_vehicle = self.env['fleet.vehicle'].search([], limit=1, order='unit_no')
        self.log.info('last Vehicle Name %s', last_vehicle.name)
        attr = vars(last_vehicle)
        self.log.info(dump_obj(last_vehicle))
        record = super(ThomasFleetVehicle, self).create(data)
        self.log.info('Unit # %s', record.unit_no)
        right_now_yr = int(date.today().strftime('%y'))
        if not record.unit_no:
            self.log.info("Inside the if")
            if last_vehicle.unit_no:
                cur_unit_no_yr = int(last_vehicle.unit_no[0:2])
                self.log.info('Unit Yr %d', cur_unit_no_yr)
                if right_now_yr - cur_unit_no_yr == 0:
                    record.unit_no = str(int(last_vehicle.unit_no) + 1)
                else:
                    record.unit_no = str(right_now_yr * 100)
            else:
                record.unit_no = str(right_now_yr * 100)
        record.protractor_guid = uuid.uuid4()
        #record.update_protractor()
        self.log.info('-----=-Returning record------------------------')
        self.log.info(record.protractor_guid)
        self.log.info('-----------------------------------------------')
        return record

    @api.depends('stored_protractor_guid')
    def _search_protractor_invoices(self):
        for rec in self:
            print("SEARCH INVOICES for ::" + rec.stored_protractor_guid)
            if rec.protractor_invoices:
                for inv in rec.protractor_invoices:
                    print("INVOICE:::" + inv.name)
            if rec.stored_protractor_guid == '2fbce895-e680-4960-a189-5dc233b3bc6a':
                inv1 = {'vehicle_id': rec.id, 'protractor_guid': rec.stored_protractor_guid, 'name': 'Test 1',
                        'description': 'Test 1', 'workOrderNumber': 'Test 1', 'invoiceNumber': 'Test 1'}
                inv2 = {'vehicle_id': rec.id, 'protractor_guid': rec.stored_protractor_guid, 'name': 'Test 2',
                        'description': 'Test 2', 'workOrderNumber': 'Test 2', 'invoiceNumber': 'Test 2'}
                rec.protractor_invoices = [(0, 0, inv1), (0, 0, inv2)]
                for inv in rec.protractor_invoices:
                    print("SEARCH INVOICE:::" + str(inv.vehicle_id) + "::::" + inv.name)

                inv_model = self.env['thomasfleet']

                rec.onchange({'protractor_invoices': [(0,0,inv1),(0,0,inv2)]},['vin_id'],rec._onchange_spec())
            else:
                rec.protractor_invoices = []

    @api.onchange('vin_id')
    def onchange_vin(self):
        print('STORED PROTRACTOR GUID CHANGED MF')

    def _get_protractor_invoices(self):
        #print("Getting Protarctor Invoices for Vehicle: " + str(self.name))
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/"+str(self.stored_protractor_guid)+"/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2014-11-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)


        self.log.info("Invoice details" + response.text)


        data = response.json()
        invoices=[]
        for item in data['ItemCollection']:
           # print("===ITEM ===")
           # print(item)
           # print("Invoice Number:"+str(item['InvoiceNumber']))
           # print("WorkOrder Number:" + str(item['WorkOrderNumber']))
           # print("Invoice Time:" + str(item['InvoiceTime']))
           # print("Summary:" + str(item['Summary']))
            inv={'vehicle_id': self.id,
                 'protractor_guid': self.stored_protractor_guid,
                 'workOrderNumber': item['WorkOrderNumber'],
                 'invoiceNumber': item['InvoiceNumber']}
            if 'Summary' in item:
                inv['grandTotal'] = item['Summary']['GrandTotal']
                inv['netTotal'] = item['Summary']['NetTotal']
                inv['laborTotal'] = item['Summary']['LaborTotal']
                inv['partsTotal'] = item['Summary']['PartsTotal']
                inv['subletTotal'] = item['Summary']['SubletTotal']
            invDT = str(item['InvoiceTime']).split("T")
            inv['invoiceDate']= invDT[0]
            inv['invoiceTime']= invDT[1]
            if 'Technician' in item:
                inv['technichan'] = str(item['Technician']['Name'])
            if 'ServiceAdvisor' in item:
                inv['serviceAdvisor'] = str(item['ServiceAdvisor']['Name'])
            if 'Header' in item:
                per =str(item['Header']['LastModifiedBy'])
                uName = per.split("\\")
                #print(uName)
                inv['lastModifiedBy'] = uName[1]

            #inv = {'vehicle_id': self.id, 'protractor_guid': self.stored_protractor_guid, 'workOrderNumber': item['WorkOrderNumber'], 'invoiceNumber': item['InvoiceNumber'], 'grandTotal': gt, 'laborTotal': lt, 'netTotal': nt, 'partsTotal': pt, 'subletTotal': slt, 'technichan': tech, 'serviceAdvisor': sA, 'invoiceTime': iT, 'lastModifiedBy': lMB}
            invoices.append((0,0,inv))

        self.update({'protractor_invoices': invoices})
        #return response.text



    def _set_protractor_invoices(self):
        #res = []
        #inv1 = self.env['thomasfleet.invoice'].new({'vehicle_id': self.id, 'protractor_guid': self.stored_protractor_guid, 'name': 'Test 1','description': 'Test 1', 'workOrderNumber': 'Test 1', 'invoiceNumber': 'Test 1'})
        #inv2 = self.env['thomasfleet.invoice'].new({'vehicle_id': self.id, 'protractor_guid': self.stored_protractor_guid, 'name': 'Test 2','description': 'Test 2', 'workOrderNumber': 'Test 2', 'invoiceNumber': 'Test 2'})

        #res.append(inv1)
        #res.append(inv2)
        #self.protractor_invoices = res
        #self.update({'protractor_invoices': [(0,0,inv1),(0,0,inv2)]})

        #get invoices for stored_guid
        #search for invoices in odoo for vehicle id
        #determine if new invoices need to be added
        #add if needed else return


        for rec in self:
            #res =[]
            print("GET INVOICES for ::" + rec.stored_protractor_guid + "ID:::" + str(rec.id))

            if rec.stored_protractor_guid == '2fbce895-e680-4960-a189-5dc233b3bc6a':
                if rec.protractor_invoices: #don't add invoices right now if there are some
                    for inv in rec.protractor_invoices:
                        print("DELETING INVOICE:::" + inv.invoiceNumber)
                        inv.unlink()

                else: #add two invoices for testing
                    print("adding two invoices")
                    inv1 = {'vehicle_id': rec.id,'protractor_guid':rec.stored_protractor_guid,'name':'Test 1','description':'Test 1','workOrderNumber':'Test 1','invoiceNumber':'Test 1'}
                    inv2 = {'vehicle_id': rec.id,'protractor_guid':rec.stored_protractor_guid,'name':'Test 2','description':'Test 2','workOrderNumber': 'Test 2','invoiceNumber':'Test 2'}
                    rec.update({'protractor_invoices': [(0, 0, inv1), (0, 0, inv2)]})
                #res.append(inv1)
                #res.append(inv2)
                #rec.protractor_invoices= [(0,0,inv1),(0,0,inv2)]
                #for inv in rec.protractor_invoices:
                 #   print("INVOICE:::" + str(inv.vehicle_id) +"::::"+ inv.name)
                #rec.onchange({'protractor_invoices': [(0,0,inv1),(0,0,inv2)]},['protractor_invoices'],rec._onchange_spec())

            #rec.update({'protractor_invoices':[(0,0,inv1),(0,0,inv2)]})

        #for rec in self:
           # print ("LOOPING RECS " + str(rec.protractor_guid))
           # rec.protractor_invoices = [(0,0,in1),(0,0,in2)]


        #return {'type': 'ir.actions.client', 'tag': 'reload'}
        #invoices = []
        #invoices = self.env['thomasfleet.protractor_invoice']
        #for invoice in invoices:
        #    invoice.invoiceNumber="TEST 1"
        #    print("Invoice # " + str(invoice.invoiceNumber))
        #invoices.append((self.id,filledInvoice1))
       # print(filledInvoice1[0].invoiceNumber)
        #invoice2 = self.env['thomasfleet.protractor_invoice']
        #invoice2.create({'name': 'Test 2', 'description': 'Test 2', 'workOrderNumber': 'Test 2', 'invoiceNumber': 'Test 2'})
        #invoices.append((self.id, invoice2))
        #for invoice in invoices:
          #  print(invoice.invoiceNumber)


    @api.multi
    def act_get_invoices(self):
        print("INVOICE ACTION")
        print('SELF ID ' + str(self.id))
        for rec in self:
            if rec.protractor_invoices:  # don't add invoices right now if there are some
                for inv in rec.protractor_invoices:
                    print("DELETING INVOICE:::" + str(inv.invoiceNumber))
                    inv.unlink()

        self._get_protractor_invoices()

        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_invoice_action')
        res.update(
        context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
        domain=[('vehicle_id', '=', self.id)]
        )
        return res


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


class ThomasFleetAssetClass(models.Model):
    _name = 'thomasfleet.asset_class'

    name = fields.Char('Asset Class')
    description = fields.Char('Description')


class ThomasFleetInsuranceClass(models.Model):
    _name = 'thomasfleet.insurance_class'

    name = fields.Char('Insurance Class')
    description = fields.Char('Description')

class ThomasFleetInvoiceClass(models.Model):
    _name = 'thomasfleet.invoice'
    _res = []
    #vehicle_id = fields.Char()
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    protractor_guid = fields.Char('Protractor GUID',related='vehicle_id.protractor_guid')
    #name = fields.Char('Name')
    #description = fields.Char('Description')
    invoiceTime = fields.Char('Invoice Time')
    invoiceDate = fields.Char('Invoice Date')
    technichan = fields.Char('Technichan')
    serviceAdvisor = fields.Char('Service Advisor')
    lastModifiedBy = fields.Char('Last Modified By')
    workOrderNumber = fields.Char('Work Order Number')
    invoiceNumber = fields.Char('Invoice Number')
    partsTotal = fields.Float('Parts Total')
    subletTotal= fields.Float('Sublet Total')
    grandTotal=fields.Float('Grand Total')
    laborTotal=fields.Float('Labor Total')
    netTotal=fields.Float('Net Total')


    def get_invoices(self):
        vehicle = self.context.get('active_id', False)
        print('COMPUTE Vehicle ID' + str(vehicle ))
        # dump_obj(vehicle)
        # self.vehicle_id = self.context.get('active_id', False)
        # print ("GETTTING INVOICES")
        # print (self.vehicle_id.protractor_guid)
        # self.protractor_guid = self.vehicle_id.protractor_guid
        #self.name = 'test'
        #self.description = 'test'
        #self.workOrderNumber = 'test'
        #self.invoiceNumber = 'test'

        # print(self.workOrderNumber)

    '''
    def browse(self, arg=None, prefetch=None):

        print("IN INVOICE BROWSE" + str(arg) +str(prefetch))
        inv = super(ThomasFleetInvoiceClass, self).browse(arg,prefetch)
        for item in inv:
            print("ITEM ::" + str(item))
        return inv

    def search(self, args, offset=0, limit=None, order=None, count=False):
        print("IN INVOICE SEARCH")
   
    def create(self, vals):
        print("IN INVOICE CREATE")
        for val in vals:
            print("VALS::"+ val)

    def browse(self, arg=None, prefetch=None):
        print("IN INVOICE BROWSE")
        for ar in arg:
            print("ARG "+ str(ar))
        return self._res[0]

    def search(self, args, offset=0, limit=None, order=None, count=False):
        print("IN INVOICE SEARCH")

        vID=''
        for arg in args:
            print(arg)
            if str(arg[0]) =='vehicle_id':
                vID = str(arg[2][0])
                print(vID)
            else:
                print(str(arg[0]) +"==" +str(arg[2]))

        inv1 = self.env['thomasfleet.invoice'].new({'vehicle_id': vID, 'name': 'Test 1', 'description': 'Test 1', 'workOrderNumber': 'Test 1', 'invoiceNumber': 'Test 1'})
        inv2 = self.env['thomasfleet.invoice'].new({'vehicle_id': vID, 'name': 'Test 2', 'description': 'Test 2', 'workOrderNumber': 'Test 2', 'invoiceNumber': 'Test 2'})

        print("VEC ID" + vID)
        self._res.append(inv1)
        self._res.append(inv2)
        return self._res


    def _get_vehicle_id(self):
        print("in Default get")
        print("ACTIVE ID:::" + str(self.env['fleet.vehicle'].name))
        print("ACTIVE ID:::" + self.env.context['active_id'])
        for rec in self:
            print("ACTIVE ID:::" + rec.env.context['active_id'])
            print("Rec Name-->" + str(self.env.fleet.vehicle.name))
            print("Current Vehicle ID-->" +  str(rec.vehicle_id.id))
            #rec.vehicle_id = self.vehicle_id
        #vehicle = self.env.context.get('active_id', False)
        #print("Vehicle: "+ str(vehicle))
        # dump_obj(vehicle)
        # self.vehicle_id = self.context.get('active_id', False)
        # print ("GETTTING INVOICES")

        #return self.context.get('active_id', False)

    
   

    @api.model
    def search_invoices(self, args, offset=0, limit=None, order=None, count=False):

        inv1 = {'name':'test', 'description':'test', 'workOrderNumber':'test','invoiceNumber':'test'}
        record = self.env['thomasfleet.invoice']
        record.update(inv1)
        return record
   

    @api.multi
    def search(self, args, offset=0, context=None,domain=None, limit=None, order=None, count=False):
        print("Search")
        for a in args:
            veh = a[2][0]
            print(str(veh))

        in1 = self.env['thomasfleet.invoice'].create({'id':'5','vehicle_id': veh,
               'name': 'Test 1',
               'description': 'Test 1',
               'workOrderNumber': 'Test 1',
               'invoiceNumber': 'Test 1'})
        in2 = self.env['thomasfleet.invoice'].create({'id':'6','vehicle_id': veh,
               'name': 'Test 2',
               'description': 'Test 2',
               'workOrderNumber': 'Test 2',
               'invoiceNumber': 'Test 2'})
        hits = self.env['thomasfleet.invoice'].search([])
        hits.append(in1)
        hits.append(in2)
        return hits
        #self._all_invoices =[(0, 0, in1), (0, 0, in2)]
        #return [(0, 0, in1), (0, 0, in2)]

    @api.multi
    def browse(self, arg=None, prefetch=None):
        #for a in arg:
         #   veh = a[2]
        print("Browse" + str(arg))
        return self._all_invoices

     #record = self.env['thomasfleet.invoice'].new({'name': 'test', 'description': 'test', 'workOrderNumber': 'test', 'invoiceNumber': 'test'})
        #print(record['name'])
       # return self.new({'name': 'test', 'description': 'test', 'workOrderNumber': 'test', 'invoiceNumber': 'test'})
    '''
    #@api.onchange('vehicle_id')
    #def _onchange_vehicle(self):
    #    if self.vehicle_id:
   # @api.onchange('vehicle_id')
    #def _onchange_vehicle(self):
     #   print('Vehicle ID changed '+ str(self.vehicle_id.stored_protractor_guid))


class ThomasFleetAccessory(models.Model):
    _name = 'thomasfleet.accessory_class'

    name = fields.Char('Accessory Name')
    description = fields.Char('Description')
    unit_no = fields.Char('Unit #')
    thomas_purchase_price = fields.Float('Thomas Purchase Price')
    purchase_date = fields.Char('Purchase Date')
    type = fields.Char('Accessory Type')
    #     name = fields.Char()
    #     value = fields.Integer()
    #     value2 = fields.Float(compute="_value_pc", store=True)
    #     description = fields.Text()
    #
    #     @api.depends('value')
    #     def _value_pc(self):
    #         self.value2 = float(self.value) / 100
