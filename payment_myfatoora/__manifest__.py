# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2021. All rights reserved.


{
    'name': 'MyFatoorah Payment gateway Integration',
    'version': '15.0.0.1.3',
    'summary': """ MyFatoorah Payment gateway Integration""",
    'description': """MyFatoorah Payment gateway Integration""",
    'category': 'Website',
    'sequence': 1,
    'author': 'Technaureus Info Solutions Pvt. Ltd.',
    'website': "http://www.technaureus.com/",
    'price': 90,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'depends': ['payment'],
    'live_test_url': 'https://www.youtube.com/watch?v=vPGQpV6uV5A',
    'data': [
        'views/payment_myfatoora_templates.xml',
        'data/payment_acquirer_data.xml',
        'views/payment_views.xml',
        'views/pay_card_template.xml',
        'views/payment_error_page.xml',

    ],
    'qweb': [],
    'images': ['images/main_screenshot.gif'],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
