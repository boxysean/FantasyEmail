from smtpd import PureProxy
import asyncore
import sys
import email
from Mail import Mail
from CheckMail import AwardPoints
import sqlite3
import yaml

import ComputeScores
import ComputeEmailerScores

DEBUGSTREAM = sys.stderr

class RiskyListyProxy(PureProxy):
  silent = True

  def setAwardPoints(self, ap):
    self.awardPoints = ap

  def process_message(self, peer, mailfrom, rcpttos, data):
    if not self.silent:
      lines = data.split('\n')
      i = 0
      for line in lines:
        if not line:
          break
        i += 1
      lines.insert(i, 'X-Peer: %s' % peer[0])
      data = NEWLINE.join(lines)

    refused = None

    if "nosend@riskylisty.com" in rcpttos:
      print >> DEBUGSTREAM, "incoming message"
    #  print >> DEBUGSTREAM, data
      # tie this in with risky listy

      msg = email.message_from_string(data)
      for i, m in enumerate(msg.walk()):
        if i == 3:
          print >> DEBUGSTREAM, "checking..."
          mail = Mail(m)
          self.awardPoints.checkEmail(mail, self.conn)
          ComputeScores.main()
          ComputeEmailerScores.main()
          print >> DEBUGSTREAM, "...done!"
    else:
      print >> DEBUGSTREAM, "sending... (%s -> %s)" % (mailfrom, rcpttos)
      refused = self._deliver(mailfrom, rcpttos, data)
      print >> DEBUGSTREAM, "...finished"

    if refused:
      print >> DEBUGSTREAM, 'we got some refusals:', refused

if __name__ == "__main__":
  config = yaml.load(file("game.yaml"))

  conn = sqlite3.connect(config["db"])

  ap = AwardPoints(conn)

  proxy = RiskyListyProxy(("127.0.0.1", 8025), ("10.8.0.6", 25))
  proxy.setAwardPoints(ap)
  proxy.conn = conn

  try:
    asyncore.loop()
  except KeyboardInterrupt:
    pass

  conn.close()

