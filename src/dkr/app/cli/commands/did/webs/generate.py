# -*- encoding: utf-8 -*-
"""
dkr.app.cli.commands module

"""
import argparse
import json
import os

from hio.base import doing
from keri.core import coring, eventing
from keri.app import habbing, oobiing
from keri.app.cli.common import existing
from keri.db import basing, dbing
from keri.help import helping

from dkr.core import didding
from dkr.core import webbing

parser = argparse.ArgumentParser(description='Generate a did:webs DID document and KEL/TEL file')
parser.set_defaults(handler=lambda args: handler(args),
                    transferable=True)
parser.add_argument('-n', '--name',
                    action='store',
                    default="dkr",
                    help="Name of controller. Default is dkr.")
parser.add_argument('--base', '-b', help='additional optional prefix to file location of KERI keystore',
                    required=False, default="")
parser.add_argument('--passcode', help='22 character encryption passcode for keystore (is not saved)',
                    dest="bran", default=None)  # passcode => bran
parser.add_argument("--did", "-d", help="DID to generate (did:webs method)", required=True)
parser.add_argument("--oobi", "-o", help="OOBI to use for resolving the AID", required=False)


def handler(args):
    gen = Generator(name=args.name, base=args.base, bran=args.bran, did=args.did, oobi=args.oobi)
    return [gen]


class Generator(doing.DoDoer):

    def __init__(self, name, base, bran, did, oobi):

        self.hby = existing.setupHby(name=name, base=base, bran=bran)
        hbyDoer = habbing.HaberyDoer(habery=self.hby)  # setup doer
        obl = oobiing.Oobiery(hby=self.hby)
        self.did = did
        self.oobi = oobi

        self.toRemove = [hbyDoer] + obl.doers
        doers = list(self.toRemove) + [doing.doify(self.generate)]
        super(Generator, self).__init__(doers=doers)

    def generate(self, tymth, tock=0.0, **opts):
        self.wind(tymth)
        self.tock = tock
        _ = (yield self.tock)

        domain, port, path, aid = didding.parseDIDWebs(self.did)
        obr = basing.OobiRecord(date=helping.nowIso8601())
        obr.cid = aid
        self.hby.db.oobis.pin(keys=(self.oobi,), val=obr)

        while self.hby.db.roobi.get(keys=(self.oobi,)) is None:
            _ = yield tock
            
        oobiHab = self.hby.habs[aid]
        msgs = oobiHab.replyToOobi(aid=aid, role="controller", eids=None)
        
        # Create the directory (and any intermediate directories in the given path) if it doesn't already exist
        kc_dir_path = f"{webbing.KC_DEFAULT_DIR}/{aid}"
        if not os.path.exists(kc_dir_path):
            os.makedirs(kc_dir_path)

        # File path
        kc_file_path = os.path.join(kc_dir_path, f"{webbing.KERI_CESR}")
        kcf = open(kc_file_path, "w")
        kcf.write(msgs.decode("utf-8"))

        #generate did doc
        diddoc = didding.generateDIDDoc(self.hby, did=self.did, aid=aid, oobi=self.oobi)
        
        # Create the directory (and any intermediate directories in the given path) if it doesn't already exist
        dd_dir_path = f"{webbing.DD_DEFAULT_DIR}/{aid}"
        if not os.path.exists(dd_dir_path):
            os.makedirs(dd_dir_path)
        
        dd_file_path = os.path.join(dd_dir_path, f"{webbing.DID_JSON}")
        ddf = open(dd_file_path, "w")
        json.dump(didding.toDidWeb(diddoc), ddf)
        
        kever = self.hby.kevers[aid]

        # construct the KEL

        pre = kever.prefixer.qb64
        preb = kever.prefixer.qb64b

        kel = []
        for fn, dig in self.hby.db.getFelItemPreIter(preb, fn=0):
            try:
                event = eventing.loadEvent(self.hby.db, preb, dig)
            except ValueError as e:
                raise e

            kel.append(event)

        key = dbing.snKey(pre=pre, sn=0)
        # load any partially witnessed events for this prefix
        for ekey, edig in self.hby.db.getPweItemsNextIter(key=key):
            pre, sn = dbing.splitKeySN(ekey)  # get pre and sn from escrow item
            try:
                kel.append(eventing.loadEvent(self.hby.db, pre, edig))
            except ValueError as e:
                raise e

        # load any partially signed events from this prefix
        for ekey, edig in self.hby.db.getPseItemsNextIter(key=key):
            pre, sn = dbing.splitKeySN(ekey)  # get pre and sn from escrow item
            try:
                kel.append(eventing.loadEvent(self.hby.db, pre, edig))
            except ValueError as e:
                raise e


        result = dict(
            didDocument=diddoc,
            pre=pre,
            state=kever.state()._asdict(),
            kel=kel
        )
        didData = json.dumps(result, indent=2)

        print(didData)
        self.remove(self.toRemove)
        return True
