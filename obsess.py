from threading import Timer
from urllib2 import Request, urlopen, URLError
import json, thread, random, sys, time

class Obsess:
    def run(self, f):
        #Read the config file provided by user
        config = ''
        with open(f) as config_file:
            config = json.load(config_file)
        #Read all test configs and schedule them
        for test in config:
            thread.start_new_thread(self.schedule_and_run, (test,))
            
    def schedule_and_run(self, test):
        print 'Running test ', test['name']
        print 'This test will run every', test['interval'], ' seconds'
        self.base_url = test['base_url']
        for url in test['urls']:
            self.test_endpoint(url)
        if test['periodic']==True:
            Timer(int(test['interval']), self.schedule_and_run, [test]).start()
        
    def test_endpoint(self, url):
        print 'Testing ', url['name']
        data = self.load_data_from_endpoint(url['endpoint'])
        if data==None:
            return
        if len(data)==0:
            if url['empty_ok']==True:
                return
            else:
                print 'Error: Got empty array'
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
        print 'Accessing endpoint ', self.base_url + endpoint
        request = Request(self.base_url + endpoint)
        try:
            response = urlopen(request)
            data = response.read()
            try:
                return json.loads(data)
            except ValueError, error:
                print 'Error: Did not get valid data'
                return None
        except URLError, e:
            print 'Error: Could not access url:', self.base_url + endpoint, 'Got an error code:', e
            
    def check_has(self, data, fields):
        for field in fields:
            if (not field in data) or data[field]=='':
                print 'Error: Field ', field, ' is not present or empty in ', data
                
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
                print 'Error: ', one_cond['child'], ' is not present in ', full_data
                
    def follow(self, url, data):
        if 'follow' in url and len(url['follow']) > 0:
            for f in url['follow']:
                for p in f['parameters']:
                    f['endpoint'] = f['pattern'].replace('{{'+p+'}}', str(data[p]))
                self.test_endpoint(f)
                
                
if __name__ == '__main__':
    print 'Using configuration file ', sys.argv[1]
    Obsess().run(sys.argv[1])
    while 1:
        time.sleep(10000)