import os
import warnings

import hvac
from ansible.module_utils.basic import AnsibleModule


def hashivault_init(readonly=True):
    argument_spec = dict(
        url = dict(required=False, default=os.environ.get('VAULT_ADDR', ''), type='str'),
        verify = dict(required=False, default=(not os.environ.get('VAULT_SKIP_VERIFY', '')), type='bool'),
        authtype = dict(required=False, default='token', type='str'),
        token = dict(required=False, default=os.environ.get('VAULT_TOKEN', ''), type='str'),
        username = dict(required=False, type='str'),
        password = dict(required=False, type='str'),
        secret = dict(required=True, type='str'),
    )
    if readonly:
        argument_spec['register'] = dict(required=False, type='str')
    else:
        argument_spec['update'] = dict(required=False, default=False, type='bool')
        argument_spec['data'] = dict(required=False, default={}, type='dict')
    return AnsibleModule(argument_spec=argument_spec)


def hashivault_client(params):
    url = params.get('url')
    verify = params.get('verify')
    token = params.get('token')
    authtype = params.get('authtype')
    token = params.get('token')
    username = params.get('username')
    password = params.get('password')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = hvac.Client(url=url, verify=verify)
        if authtype == 'github':
            client.auth_github(token)
        elif authtype == 'userpass':
            client.auth_userpass(username, password)
        elif authtype == 'ldap':
            client.auth_ldap(username, password)
        else:
            client.token = token
    return client


def hashivault_read(params):
    result = { "changed": False, "rc" : 0}
    try:
        client = hashivault_client(params)
        secret = params.get('secret')
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = client.read('%s' % secret)
            if not response:
                result['rc'] = 1
                result['failed'] = True
                result['msg'] = "Secret %s is not in vault" % secret
                return result
            result['data'] = response['data']
            result['lease_id'] = response['lease_id']
            result['lease_duration'] = response['lease_duration']
    except Exception as e:
        import traceback
        result['rc'] = 1
        result['failed'] = True
        result['msg'] = "Exception: " + str(e)
        result['stack_trace'] = traceback.format_exc()
    return result


def hashivault_write(params):
    result = { "changed": False, "rc" : 0}
    try:
        client = hashivault_client(params)
        secret = params.get('secret')
        data = params.get('data')
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if params.get('update'):
                read_data = client.read('%s' % secret)
                if read_data and 'data' in read_data:
                    write_data  = read_data['data']
                else:
                    write_data  = {}
                write_data.update(data)
                client.write(('%s' % secret), **write_data)
                result['msg'] = "Secret %s updated" % secret
            else:
                result['data'] = client.write(('%s' % secret), **data)
                result['msg'] = "Secret %s written" % secret
        result['changed'] = True
    except Exception as e:
        import traceback
        result['rc'] = 1
        result['failed'] = True
        result['msg'] = "Exception: " + str(e)
        result['stack_trace'] = traceback.format_exc()
    return result
