def captcha_field(request=request):
    from gluon.tools import Recaptcha2
    w = lambda x, y: Recaptcha2(request,
                                '6LeBjrcUAAAAABPDnsWu-2qxvAwgRnS4PfYDjBbu',
                                '6LeBjrcUAAAAAD29Ae0vf4Y9YDaNlTfMB1Sk7dMt',
                                error_message='Invalid, please try again.')
    return Field('captcha', 'string', label=T('Verify'), widget=w, default='ok')
