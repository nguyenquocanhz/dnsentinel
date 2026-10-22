# -*- coding: utf-8 -*-
"""Ngoai le nghiep vu."""


class DNSentinelError(Exception):
    """Goc."""


class DomainInvalid(DNSentinelError):
    """Ten mien khong hop le (rong / sai dinh dang / khong phai .vn)."""


class DomainExists(DNSentinelError):
    """Ten mien da ton tai trong danh sach."""


class DomainNotFound(DNSentinelError):
    """Khong tim thay ten mien."""


class ResolveError(DNSentinelError):
    """Loi khi truy van DNS (timeout, socket, goi tin hong...)."""
