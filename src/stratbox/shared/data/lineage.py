"""Exact, validated input evidence without executable state or component releases."""
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


def _identity(value):
    return None if value is None else {'sha256':value.sha256,'size':value.size}


def _read_identity(value):
    if not isinstance(value,dict) or set(value)!={'sha256','size'} or type(value['size']) is not int:
        raise ValueError('lineage.identity_invalid')
    return ByteIdentity(value['sha256'],value['size'])


def input_value(value):
    if not isinstance(value,UsedInputReceipt):raise TypeError('lineage.input_required')
    result={'role':value.role,'identity':_identity(value.identity),'media_type':value.media_type,
        'availability':value.availability,'source_id':value.source_id,'container':_identity(value.container),
        'member':value.member,'content_basis':_identity(value.content_basis)}
    input_from(result)
    return result


def input_from(value):
    keys={'role','identity','media_type','availability','source_id','container','member','content_basis'}
    if not isinstance(value,dict) or set(value)!=keys:
        raise ValueError('lineage.input_invalid')
    return UsedInputReceipt(value['role'],_read_identity(value['identity']),value['media_type'],value['availability'],
        value['source_id'],_read_identity(value['container']) if value['container'] else None,value['member'],
        _read_identity(value['content_basis']) if value['content_basis'] else None)
