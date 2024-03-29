# -*- coding: utf-8 -*-
{
    'name': "thomasfleet",

    'summary': """
        Extend and customize Odoo Fleet module to meet Thomas Solution requirements""",

    'description': """
        Extend and customize Odoo Fleet module to meet Thomas Solution requirements
    """,

    'author': "Andrew Bates",
    'website': "http://www.kadabby.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Thomas',
    'version': '0.258',


    # any module necessary for this one to work correctly
    'depends': ['base','fleet','account'],

    # always loaded
    'data': [
        'security/thomasfleet_security.xml',
        'security/ir.model.access.csv',
        'views/message_views.xml',
        'views/views.xml',
        'views/lease_views.xml',
        'views/customer_views.xml',
        'views/invoice_views.xml',
        'views/templates.xml',
        'views/product_views.xml',
        #'report/custom_header_template.xml',
        'report/lease_print_template.xml',
        'report/lease_printout.xml',
        'report/invoice_report_template.xml',
        'data/fleet.vehicle.state.csv',
        'data/thomasfleet.lease_status.csv',
        'data/thomasfleet.location.csv',
        'data/thomasfleet.floormaterial.csv',
        'data/thomasfleet.fueltype.csv',
        'data/thomasfleet.seatmaterial.csv',
        'data/thomasfleet.asset_class.csv',
        'data/thomasfleet.insurance_class.csv',
        #'data/thomasfleet.remove_makes.xml',
        #'data/thomasfleet.remove_brands.xml',
       'data/fleet.vehicle.model.brand.csv',
       'data/fleet.vehicle.model.csv',
       'data/thomasfleet.trim.csv',
        'data/thomasfleet.inclusions.csv',
        'data/thomasfleet.accessory_type.csv'



    ],
    #'qweb': ['static/src/xml/utility_field_qweb.xml'],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}
