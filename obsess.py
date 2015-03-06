from threading import Timer
from urllib2 import Request, urlopen, URLError
from cStringIO import StringIO
import json, thread, random, sys, time, smtplib

class Obsess:
    def run(self, f):
        self.sys_stdout = sys.stdout
        #sys.stdout = self.stdout = StringIO()
        self.stdout = StringIO()
        #Read the config file provided by user
        config = ''
        with open(f) as config_file:
            config = json.load(config_file)
        #Read all test configs and schedule them
        for test in config:
            thread.start_new_thread(self.schedule_and_run, (test,))
            
    def schedule_and_run(self, test):
        print >>self.stdout, 'Running test ', test['name']
        print >>self.stdout, 'This test will run every', test['interval'], ' seconds'
        self.error = False
        self.notified = False
        for base in test['base_url']:
            self.base_url = base
            for url in test['urls']:
                self.test_endpoint(url)
        print self.stdout.getvalue()
        if self.error==False:
            self.notified = False
        if self.error==True and test['notification']['enable']==True:
            if 'email' in test['notification'] and test['notification']['email']['enable']==True and self.notified==False:
                self.send_email(test['notification']['email'])
                self.notified = True
        if test['periodic']==True:
            self.error = False
            self.stdout.truncate(0)
            Timer(int(test['interval']), self.schedule_and_run, [test]).start()
        
    def test_endpoint(self, url):
        print >>self.stdout, 'Testing ', url['name']
        data = self.load_data_from_endpoint(url['endpoint'])
        if data==None:
            return
        if len(data)==0:
            if url['empty_ok']==True:
                return
            else:
                print >>self.stdout, 'Error: Got empty array'
                self.error = True
                return
        if url['array']==True:
            if url['test_all']==True:
                for i in range(0, len(data)):
                    self.check_has(data[i], url['must_have'])
                    if 'child_must_have' in url:
                        self.check_child_has(data[i], url['child_must_have'])
                    self.follow(url, data[i])
                            
            else:
                i = random.randint(0, len(data) - 1)
                self.check_has(data[i], url['must_have'])
                if 'child_must_have' in url:
                    self.check_child_has(data[i], url['child_must_have'])
                self.follow(url, data[i])
        else:
            self.check_has(data, url['must_have'])
            if 'child_must_have' in url:
                self.check_child_has(data, url['child_must_have'])
            self.follow(url, data)
        
    def load_data_from_endpoint(self, endpoint):
        print >>self.stdout, 'Accessing endpoint ', self.base_url + endpoint
        request = Request(self.base_url + endpoint)
        try:
            response = urlopen(request)
            data = response.read()
            try:
                return json.loads(data)
            except ValueError, error:
                print >>self.stdout, 'Error: Did not get valid data'
                self.error = True
                return None
        except URLError, e:
            print >>self.stdout, 'Error: Could not access url:', self.base_url + endpoint, 'Got an error code:', e
            self.error = True
            
    def check_has(self, data, fields):
        for field in fields:
            if (not field in data) or data[field]=='':
                print >>self.stdout, 'Error: Field ', field, ' is not present or empty in ', data
                self.error = True
                
    def check_child_has(self, full_data, cond):
        for one_cond in cond:
            if one_cond['child'] in full_data:
                data = full_data[one_cond['child']]
                if one_cond['array']==True:
                    if one_cond['test_all']==True:
                        for i in range(0, len(data)):
                            self.check_has(data[i], one_cond['must_have'])
                            if 'child_must_have' in one_cond:
                                self.check_child_has(data[i], one_cond['child_must_have'])
                    else:
                        i = random.randint(0, len(data) - 1)
                        self.check_has(data[i], one_cond['must_have'])
                        if 'child_must_have' in one_cond:
                            self.check_child_has(data[i], one_cond['child_must_have'])
                else:
                    self.check_has(data, one_cond['must_have'])
                    if 'child_must_have' in one_cond:
                        self.check_child_has(data[i], one_cond['child_must_have'])
            else:
                print >>self.stdout, 'Error: ', one_cond['child'], ' is not present in ', full_data
                self.error = True
                
    def follow(self, url, data):
        if 'follow' in url and len(url['follow']) > 0:
            for f in url['follow']:
                for p in f['parameters']:
                    f['endpoint'] = f['pattern'].replace('{{'+p+'}}', str(data[p]))
                self.test_endpoint(f)
                
    def send_email(self, email):
        #Enable access to less secure apps here https://www.google.com/settings/security/lesssecureapps
        gmail_user = email['email_id']
        gmail_pwd = email['email_password']
        FROM = email['email_id']
        TO = email['email_to']
        SUBJECT = "API test failed"
        TEXT = self.stdout.getvalue()

        # Prepare actual message
        message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
                    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
        try:
            #server = smtplib.SMTP(SERVER) 
            server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work!
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pwd)
            server.sendmail(FROM, TO, message)
            #server.quit()
            server.close()
            print 'Successfully sent the mail'
        except:
            print "Failed to send mail"
                
                
if __name__ == '__main__':
    print 'Using configuration file ', sys.argv[1]
    Obsess().run(sys.argv[1])
    while 1:
        time.sleep(10000)