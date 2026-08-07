import gettext
import os
import random


class Voice:
    def __init__(self, lang):
        localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
        translation = gettext.translation(
            'voice', localedir,
            languages=[lang],
            fallback=True,
        )
        translation.install()
        self._ = translation.gettext

    def custom(self, s):
        return s

    def default(self):
        return self._('The bridge is quiet.')

    def on_starting(self):
        return random.choice([
            self._('Heimdall awakening ...'),
            self._('Opening the Bifrost ...'),
            self._('The watch begins.')])

    def on_ai_ready(self):
        return random.choice([
            self._('The watcher is ready.'),
            self._('The mind is awake.')])

    def on_keys_generation(self):
        return self._('Forging identity keys. Do not power off ...')

    def on_normal(self):
        return random.choice([
            '',
            self._('Watching the bridge.')])

    def on_free_channel(self, channel):
        return self._('Channel {channel} is clear.').format(channel=channel)

    def on_reading_logs(self, lines_so_far=0):
        if lines_so_far == 0:
            return self._('Reading the last watch ...')
        return self._('Read {lines_so_far} log lines so far ...').format(lines_so_far=lines_so_far)

    def on_bored(self):
        return random.choice([
            self._('The realms are quiet ...'),
            self._('Still watching.')])

    def on_motivated(self, reward):
        return self._('The watch is strong.')

    def on_demotivated(self, reward):
        return self._('The signal grows faint.')

    def on_sad(self):
        return random.choice([
            self._('Nothing stirs beyond the bridge ...'),
            self._('The watch is lonely ...'),
            '...'])

    def on_angry(self):
        return random.choice([
            '...',
            self._('Something is wrong on the bridge.'),
            self._('Eyes open. Stay alert.')])

    def on_excited(self):
        return random.choice([
            self._('Many signals across the realms!'),
            self._('The bridge is alive!'),
            self._('So much movement!'),
            self._('The watch grows interesting.')])

    def on_new_peer(self, peer):
        if peer.first_encounter():
            return self._('Another watcher approaches: {name}.').format(name=peer.name())
        return random.choice([
            self._('{name} has returned.').format(name=peer.name()),
            self._('Watcher {name} is nearby.').format(name=peer.name())])

    def on_lost_peer(self, peer):
        return random.choice([
            self._('{name} has left the bridge.').format(name=peer.name()),
            self._('Watcher {name} is gone.').format(name=peer.name())])

    def on_miss(self, who):
        return random.choice([
            self._('{name} moved beyond sight.').format(name=who),
            self._('Lost sight of {name}.').format(name=who),
            self._('Signal lost.')])

    def on_grateful(self):
        return random.choice([
            self._('The watchers stand together.'),
            self._('All realms accounted for.')])

    def on_lonely(self):
        return random.choice([
            self._('No other watchers nearby ...'),
            self._('The bridge is empty ...'),
            self._('Standing watch alone.')])

    def on_napping(self, secs):
        return random.choice([
            self._('Resting the watch for {secs}s ...').format(secs=secs),
            self._('Eyes closed briefly ...'),
            self._('Resting ({secs}s)').format(secs=secs)])

    def on_shutdown(self):
        return random.choice([
            self._('The watch ends for now.'),
            self._('Closing the Bifrost.')])

    def on_awakening(self):
        return random.choice([
            self._('Eyes opening ...'),
            self._('The watch resumes.')])

    def on_waiting(self, secs):
        return random.choice([
            self._('Watching for {secs}s ...').format(secs=secs),
            '...',
            self._('Scanning the horizon ({secs}s)').format(secs=secs)])

    def on_assoc(self, ap):
        ssid, bssid = ap['hostname'], ap['mac']
        what = ssid if ssid != '' and ssid != '<hidden>' else bssid
        return random.choice([
            self._('Observing {what}.').format(what=what),
            self._('Checking {what}.').format(what=what),
            self._('{what} is in sight.').format(what=what)])

    def on_deauth(self, sta):
        return random.choice([
            self._('Authorized test against {mac}.').format(mac=sta['mac']),
            self._('Testing station {mac}.').format(mac=sta['mac']),
            self._('Active assessment: {mac}.').format(mac=sta['mac'])])

    def on_handshakes(self, new_shakes):
        s = 's' if new_shakes > 1 else ''
        return self._('Captured {num} new handshake{plural}.').format(num=new_shakes, plural=s)

    def on_unread_messages(self, count, total):
        s = 's' if count > 1 else ''
        return self._('{count} new raven{plural} arrived.').format(count=count, plural=s)

    def on_rebooting(self):
        return self._('The horn is silent. Rebooting ...')

    def on_uploading(self, to):
        return self._('Sending ravens to {to} ...').format(to=to)

    def on_last_session_data(self, last_session):
        status = self._('Tested {num} stations\n').format(num=last_session.deauthed)
        if last_session.associated > 999:
            status += self._('Observed >999 associations\n')
        else:
            status += self._('Observed {num} associations\n').format(num=last_session.associated)
        status += self._('Captured {num} handshakes\n').format(num=last_session.handshakes)
        if last_session.peers == 1:
            status += self._('Met 1 watcher')
        elif last_session.peers > 0:
            status += self._('Met {num} watchers').format(num=last_session.peers)
        return status

    def on_last_session_tweet(self, last_session):
        return self._(
            'Heimdall watched for {duration}, tested {deauthed} clients, observed {associated} associations, and captured {handshakes} handshakes. #ProjectOdin #Heimdall').format(
            duration=last_session.duration_human,
            deauthed=last_session.deauthed,
            associated=last_session.associated,
            handshakes=last_session.handshakes)

    def hhmmss(self, count, fmt):
        if count > 1:
            if fmt == "h":
                return self._("hours")
            if fmt == "m":
                return self._("minutes")
            if fmt == "s":
                return self._("seconds")
        else:
            if fmt == "h":
                return self._("hour")
            if fmt == "m":
                return self._("minute")
            if fmt == "s":
                return self._("second")
        return fmt
