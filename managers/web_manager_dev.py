from lxml import html
import time
from lxml import etree

from seleniumwire import webdriver
#from seleniumwire import webdriver
from selenium.common.exceptions import *
import traceback
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support.ui import WebDriverWait 
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import requests
import http
import random
from amazoncaptcha import AmazonCaptcha

software_names = [SoftwareName.CHROME.value]
operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]
user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)



class NoElementFoundError(Exception):

  def __init__(self, error):
    self.error = error

  def __str__(self):
    return str("NoElementFoundError of xpath: ") + str(self.error) + "\n"


class WebMgrErr(Exception):
  
  def __init__(self, error):
    self.error = error

  def __str__(self):
    return str("WebMgrErr: ") + "\n" + str(self.error)


class WebManager():

  def __init__(self):
      self.drivers = []
      self.settings = {}

  def init(self, settings):
    try:
      self.settings = settings
      num_driver = settings.get('num_driver', 1)
      option = Options()
      #option = webdriver.ChromeOptions()
      
      option.add_argument('--headless')
      option.add_argument('--window-size=1920x1080')
      option.add_argument('window-size=1920x1080')
      option.add_argument('--disable-gpu')
      option.add_argument('--start-maximized')
      option.add_argument('--no-proxy-server')
      option.add_argument('--no-sandbox')
      option.add_argument('--blink-settings=imagesEnabled=false')
      option.add_argument('--lang=en_US')
      option.add_argument('--disable-dev-shm-usage')
      option.add_argument('disable-dev-shm-usage')
      prefs = {"profile.managed_default_content_settings.images": 2}
      option.add_experimental_option("prefs", prefs)

      driver_path = settings.get('chromedriver_path', './web_drivers/chromedriver')
      
      self.javascripts = {
        'style': './managers/SerializeWithStyles.js'
      }

      for javascript in self.javascripts.keys():
        f = open('./managers/SerializeWithStyles.js')
        code = f.read()
        f.close()
        self.javascripts[javascript] = code

      for i in range(num_driver):
        user_agent = settings['chromedriver_user_agent']
        #user_agent = user_agent_rotator.get_random_user_agent()
        option.add_argument('--user-agent={}'.format(user_agent))
        #user_agent = user_agent_rotator.get_random_user_agent()
        
        #driver = webdriver.Chrome(driver_path, chrome_options = option)
        driver = webdriver.Chrome(driver_path, options = option)
        driver.set_page_load_timeout(600)
        driver.get('about:blank')
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});")
        self.drivers.append(driver)
      self.driver_idx = 0
    except Exception as e:
      raise WebMgrErr(e)

  def restart(self,sleep_time):
    try:
      for driver in self.drivers:
        driver.quit()
      self.drivers = []
      time.sleep(sleep_time)
      num_driver = self.settings.get('num_driver', 1)
      option = Options()
      #option = webdriver.ChromeOptions()
      option.add_argument('--headless')
      option.add_argument('--window-size=1920x1080')
      option.add_argument('window-size=1920x1080')
      option.add_argument('--disable-gpu')
      option.add_argument('--start-maximized')
      option.add_argument('--no-proxy-server')
      option.add_argument('--no-sandbox')
      option.add_argument('--blink-settings=imagesEnabled=false')
      option.add_argument('--lang=en_US')
      option.add_argument('--disable-dev-shm-usage')
      option.add_argument('disable-dev-shm-usage')
      prefs = {"profile.managed_default_content_settings.images": 2}
      option.add_experimental_option("prefs", prefs)

      #print(self.settings)
      driver_path = self.settings.get('chromedriver_path', './web_drivers/chromedriver')
      
      self.javascripts = {
        'style': './managers/SerializeWithStyles.js'
      }

      for javascript in self.javascripts.keys():
        f = open('./managers/SerializeWithStyles.js')
        code = f.read()
        f.close()
        self.javascripts[javascript] = code

      for i in range(num_driver):
        user_agent = self.settings['chromedriver_user_agent']
        #user_agent = user_agent_rotator.get_random_user_agent()
        option.add_argument('--user-agent={}'.format(user_agent))
        driver = webdriver.Chrome(driver_path, options = option)
        #driver = webdriver.Chrome(driver_path, chrome_options = option)
        driver.set_page_load_timeout(600)
        driver.get('about:blank')
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});")
        self.drivers.append(driver)
      self.driver_idx = 0
    except Exception as e:
      raise WebMgrErr(e)

  def close(self):
    try:
      print(self.drivers)
      for driver in self.drivers:
        driver.quit()
    except Exception as e:
      raise WebMgrErr(e)

 
  def get_cur_driver_(self):
    return self.drivers[self.driver_idx]


  def rotate_driver_(self):
    self.driver_idx += 1
    if self.driver_idx == len(self.drivers):
      self.driver_idx = 0


  def store_page_source(self, name):
    try:
      driver = self.get_cur_driver_()
      f = open(name, 'w')
      page_source = driver.page_source
      lxml_tree = html.fromstring(page_source)
      f.write(etree.tostring(lxml_tree, encoding='unicode', pretty_print=True))
      f.close()
    except Exception as e:
      raise WebMgrErr(e)


  def get_html(self):
    try:
      driver = self.get_cur_driver_()
      page_source = driver.page_source 
      return page_source
    except Exception as e:
      raise WebMgrErr(e)


  def build_lxml_tree(self):
    try:
      driver = self.get_cur_driver_()
      page_source = driver.page_source 
      self.lxml_tree = html.fromstring(page_source)
      time.sleep(5)
    except Exception as e:
      raise WebMgrErr(e)


  def load(self, url):
    try:
      self.rotate_driver_()
      driver = self.get_cur_driver_()
      driver.get(url)
    except Exception as e:
      raise WebMgrErr(e)


  def get_current_url(self):
    try:
      driver = self.get_cur_driver_()
      return driver.current_url
    except Exception as e:
      raise WebMgrErr(e)

    
  def wait_loading(self):
    try:
      driver = self.get_cur_driver_()
      WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except Exception as e:
      raise WebMgrErr(e)


  def execute_script(self, script):
    try:
      driver = self.get_cur_driver_()
      return driver.execute_script(script)
    except Exception as e:
      raise WebMgrErr(e)
 
  def get_subtree_no_parent_with_style(self, xpath):
    try:
      driver = self.get_cur_driver_()
      elements = driver.find_elements_by_xpath(xpath)
      if len(elements) > 0:
        driver.execute_script(self.javascripts['style'])
        print(driver.execute_script('return arguments[0].innerHTML;', elements[0]))
        return driver.execute_script('return arguments[0].innerHTML;', elements[0])
      return ''
    except Exception as e:
      raise WebMgrErr(e)
  

  def get_subtree_no_parent_with_style_strong(self, xpath):
    try:
      driver = self.get_cur_driver_()
      elements = driver.find_elements_by_xpath(xpath)
      if len(elements) == 0: raise NoElementFoundError(xpath)
      driver.execute_script(self.javascripts['style'])
      print(driver.execute_script('return arguments[0].innerHTML;', elements[0]))
      return driver.execute_script('return arguments[0].innerHTML;', elements[0])
    except Exception as e:
      raise WebMgrErr(e)


 

  def get_subtree_with_style(self, xpath):
    try:
      driver = self.get_cur_driver_()
      elements = driver.find_elements_by_xpath(xpath)
      if len(elements) > 0:
        driver.execute_script(self.javascripts['style'])
        return driver.execute_script('return arguments[0].serializeWithStyles();', elements[0])
      return ''
    except Exception as e:
      raise WebMgrErr(e)
  

  def get_subtree_with_style_strong(self, xpath):
    try:
      driver = self.get_cur_driver_()
      elements = driver.find_elements_by_xpath(xpath)
      if len(elements) == 0: raise NoElementFoundError(xpath)
      driver.execute_script(self.javascripts['style'])
      return driver.execute_script('return arguments[0].serializeWithStyles();', elements[0])
    except Exception as e:
      raise WebMgrErr(e)


  def get_elements_by_selenium_(self, xpath):
    driver = self.get_cur_driver_()
    elements = driver.find_elements_by_xpath(xpath)
    print(len(elements), xpath)
    return elements


  def get_elements_by_selenium_strong_(self, xpath):
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
    elements = self.get_elements_by_selenium_(xpath)
    if len(elements) == 0:
      raise NoElementFoundError(xpath)
    return elements

  def get_elements_by_lxml_(self, xpath):
    #self.build_lxml_tree()
    elements = self.lxml_tree.xpath(xpath)
    print(len(elements), xpath)
    return elements

  def get_elements_by_lxml_strong_(self, xpath):
    elements = self.get_elements_by_lxml_(xpath)
    if len(elements) == 0:
      print("Re-build lxml tree and retry")
      self.build_lxml_tree()
      elements = self.get_elements_by_lxml_(xpath)
      if len(elements) == 0:
        raise NoElementFoundError(xpath)
    return elements


  def get_attribute_by_selenium_(self, element, attr):
    if attr == 'alltext':
      return element.text.strip()
    else:
      return element.get_attribute(attr)

  def get_attribute_by_selenium_strong_(self, element, attr):
    val = self.get_attribute_by_selenium_(element, attr)
    if val == None: raise NoElementFoundError(xpath)
    return val

  def get_attribute_by_lxml_(self, element, attr):
    if attr == 'alltext': val = ''.join(element.itertext()).strip()
    elif attr == 'text': val = element.text.strip()
    elif attr == 'innerHTML': val = etree.tostring(element, pretty_print=True)
    else: val = element.get(attr)
    if val != None: val = val.strip()
    print(val)
    return val

  def get_attribute_by_lxml_strong_(self, element, attr):
    val = self.get_attribute_by_lxml_(element, attr)
    if val == None: raise NoElementFoundError(xpath)
    return val

  def get_value_by_selenium(self, xpath, attr):
    try:
      elements = self.get_elements_by_selenium_(xpath)
      if len(elements) == 0: return None
      return self.get_attribute_by_selenium_(elements[0], attr)
    except Exception as e:
      raise WebMgrErr(e)

  def get_value_by_selenium_strong(self, xpath, attr):
    try:
      elements = self.get_elements_by_selenium_strong_(xpath)
      return self.get_attribute_by_selenium_strong_(elements[0], attr)
    except Exception as e:
      raise WebMgrErr(e)


  def login_by_xpath(self, user_id, pwd, xpath_user_id, xpath_pwd, click_xpath):
    try:
      driver = self.get_cur_driver_()
      #print(xpath_user_id)
      #elem = driver.find_element_by_xpath(xpath_user_id)
      elem1 = driver.find_element_by_id("fm-login-id")
      print(user_id)
      print(elem1)
      elem1.send_keys(user_id)
      
      #print(xpath_pwd)
      #elem = driver.find_element_by_xpath(xpath_pwd)
      elem2 = driver.find_element_by_id("fm-login-password")
      print(pwd)
      print(elem2)
      elem2.send_keys(pwd)
      print(click_xpath)
      #driver.find_element_by_xpath(click_xpath).click()
      
      inputElement = driver.find_element_by_class_name('fm-submit')
      inputElement.click()
      time.sleep(20)
      print(driver.current_url)
    except Exception as e:
      raise WebMgrErr(e)


  def get_value_by_lxml(self, xpath, attr):
    try:
      elements = self.get_elements_by_lxml_(xpath)
      if len(elements) == 0: return None
      return self.get_attribute_by_lxml_(elements[0], attr)
    except Exception as e:
      raise WebMgrErr(e)

  def get_value_by_lxml_strong(self, xpath, attr):
    try:
      elements = self.get_elements_by_lxml_strong_(xpath)
      return self.get_attribute_by_lxml_strong_(elements[0], attr)
    except Exception as e:
      raise WebMgrErr(e)

  def get_values_by_selenium(self, xpath, attr):
    try:
      elements = self.get_elements_by_selenium_(xpath)
      print(len(elements), xpath)
      if len(elements) == 0: return []
      result = []
      for element in elements:
        val = self.get_attribute_by_selenium_(element, attr)
        if val != None: result.append(val)
      return result
    except Exception as e:
      raise WebMgrErr(e) 

  def send_keys_to_elements(self, xpath, txt):
    try:
      elements = self.get_elements_by_selenium_(xpath)
      num_elements = len(elements)
      if num_elements == 0: return
      action = ActionChains(self.get_cur_driver_())
      for element in elements:
        action.send_keys_to_element(element, txt)
      action.perform()
    except Exception as e:
      elements = self.get_elements_by_selenium_(xpath)
      num_elements = len(elements)
      if num_elements == 0:
        raise WebMgrErr(e) 

  def send_keys_to_elements_strong(self, xpath, txt):
    try:
      elements = self.get_elements_by_selenium_strong_(xpath)
      action = ActionChains(self.get_cur_driver_())
      for element in elements:
        action.send_keys_to_element(element, txt)
      action.perform()
    except Exception as e:
      raise WebMgrErr(e) 


  def scroll_to_bottom(self):
    try:
      self.get_cur_driver_().execute_script("window.scrollTo(0, document.body.scrollHeight)")
      time.sleep(2)

    except Exception as e:
      raise WebMgrErr(e)



  def click_elements_repeat(self, xpath, time_sleep):
    try:
      while True:
        self.get_cur_driver_().execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)
        elements = self.get_elements_by_selenium_(xpath)
        num_elements = len(elements)
        if num_elements == 0: break
        while True:
          try:
            element = WebDriverWait(self.get_cur_driver_(), 60).until(EC.element_to_be_clickable((By.XPATH, xpath)))  
            self.get_cur_driver_().execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
            element.click()
            break;
          except:
            print("Element is not clickable, so retry")
            time.sleep(10)
            pass
      time.sleep(time_sleep)
      return
    except Exception as e:
      raise WebMgrErr(e)
      return
    return;

  def click_elements(self, xpath):
    try:
      elements = self.get_elements_by_selenium_(xpath)
      num_elements = len(elements)
      if num_elements == 0: return
      element = WebDriverWait(self.get_cur_driver_(), 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
      element.click()
      #action = ActionChains(self.get_cur_driver_())
      #for element in elements:
      #  action.click(element)
      #action.perform()
    except Exception as e:
      elements = self.get_elements_by_selenium_(xpath)
      num_elements = len(elements)
      if num_elements == 0:
        raise WebMgrErr(e) 

  def click_elements_strong(self, xpath):
    try:
      elements = self.get_elements_by_selenium_strong_(xpath)
      action = ActionChains(self.get_cur_driver_())
      for element in elements:
        action.click(element)
      action.perform()
    except Exception as e:
      raise WebMgrErr(e) 

  def move_to_elements(self, xpath):
    try:
      action = ActionChains(self.get_cur_driver_())
      elements = self.get_elements_by_selenium_(xpath)
      for element in elements:
        action.move_to_element(element)
      action.perform();
    except Exception as e:
      raise WebMgrErr(e) 

  def move_to_elements_strong(self, xpath):
    try:
      elements = self.get_elements_by_selenium_(xpath)
      if len(elements) == 0: raise NoElementFoundError(xpath)
      action = ActionChains(self.get_cur_driver_())
      for element in elements:
        action.move_to_element(element).perform();
    except Exception as e:
      raise WebMgrErr(e) 

  def get_values_by_lxml(self, xpath, attr):
    try:
      elements = self.get_elements_by_lxml_(xpath)
      if len(elements) == 0: return []
      result = []
      for element in elements:
        val = self.get_attribute_by_lxml_(element, attr)
        if val != None: result.append(val)
      return result
    except Exception as e:
      raise WebMgrErr(e) 

  def get_values_by_selenium_strong(self, xpath, attr):
    try:
      elements = self.get_elements_by_selenium_strong_(xpath)
      result = []
      for element in elements:
        val = self.get_attribute_by_selenium_(element, attr)
        if val != None: result.append(val)
      if len(result) == 0: raise NoElementFoundError(xpath)
      print(result)
      return result
    except Exception as e:
      raise WebMgrErr(e) 

  def get_values_by_lxml_strong(self, xpath, attr):
    try:
      elements = self.get_elements_by_lxml_strong_(xpath)
      result = []
      for element in elements:
        val = self.get_attribute_by_lxml_(element, attr)
        if val != None: result.append(val)
      if len(result) == 0: raise NoElementFoundError(xpath)
      return result
    except Exception as e:
      raise WebMgrErr(e) 
    
  def get_key_values_by_selenium(self, xpath, kxpath, kattr, vxpath, vattr):
    try:
      elements = self.get_elements_by_selenium_(xpath)
      if len(elements) == 0: return {}
      result = {}
      for element in elements:
        kelements = element.find_elements_by_xpath(kxpath)
        if len(kelements) == 0: continue
        key = self.get_attribute_by_selenium_(kelements[0], kattr)
        if key == None: continue
        velements = element.find_elements_by_xpath(vxpath)
        if len(velements) == 0: continue
        val = self.get_attribute_by_selenium_(velements[0], vattr)
        if val == None: continue
        result[key] = val
      return result
    except Exception as e:
      raise WebMgrErr(e)

  def get_key_values_by_lxml(self, xpath, kxpath, kattr, vxpath, vattr):
    try:
      elements = self.get_elements_by_lxml_(xpath)
      if len(elements) == 0: return {}
      result = {}
      for element in elements:
        kelements = element.xpath(kxpath)
        if len(kelements) == 0: continue
        key = self.get_attribute_by_lxml_(kelements[0], kattr)
        if key == None: continue
        velements = element.xpath(vxpath)
        if len(velements) == 0: continue
        val = self.get_attribute_by_lxml_(velements[0], vattr)
        if val == None: continue
        result[key] = val
      return result
    except Exception as e:
      raise WebMgrErr(e)

  def get_key_values_by_selenium_strong(self, xpath, kxpath, kattr, vxpath, vattr):
    try:
      elements = self.get_elements_by_selenium_strong_(xpath)
      result = {}
      for element in elements:
        kelements = element.find_elements_by_xpath(kxpath)
        if len(kelements) == 0: continue
        key = self.get_attribute_by_selenium_(kelements[0], kattr)
        if key == None: continue
        velements = element.find_elements_by_xpath(vxpath)
        if len(velements) == 0: continue
        val = self.get_attribute_by_selenium_(velements[0], vattr)
        if val == None: continue
        result[key] = val
      if len(result) == 0: raise NoElementFoundError(xpath)
      return result
    except Exception as e:
      raise WebMgrErr(e)    

  def get_key_values_by_lxml_strong(self, xpath, kxpath, kattr, vxpath, vattr):
    try:
      elements = self.get_elements_by_lxml_strong_(xpath)
      result = {}
      for element in elements:
        kelements = element.xpath(kxpath)
        if len(kelements) == 0: continue
        key = self.get_attribute_by_lxml_(kelements[0], kattr)
        if key == None: continue
        velements = element.xpath(vxpath)
        if len(velements) == 0: continue
        val = self.get_attribute_by_lxml_(velements[0], vattr)
        if val == None: continue
        result[key] = val
      if len(result) == 0: raise NoElementFoundError(xpath)
      return result
    except Exception as e:
      raise WebMgrErr(e)    

  def get_option_values_by_lxml(self, xpath, vxpath, vattr):
    try:
      elements = self.get_elements_by_lxml_(xpath)
      if len(elements) == 0: return []
      result = []
      for element in elements:
        velements = element.xpath(vxpath)
        if len(velements) == 0: continue
        res_tmp = []
        for velement in velements:
          val = self.get_attribute_by_lxml_(velement, vattr)
          res_tmp.append(val)
        result.append(res_tmp)
      return result
    except Exception as e:
      raise WebMgrErr(e)



if __name__ == '__main__':
  
  web_manager = WebManager()
  web_manager.init({"chromedriver_user_agent":"SAMPLE TEST"})
  #url = "https://item.rakuten.co.jp/golfshoplb/classicpt1a/"
  #url = "https://item.rakuten.co.jp/greenfil/pr20-rsnf-cs47/"
  #url = "https://en.zalando.de/jdy-jdynew-brighton-spring-coat-classic-coat-black-jy121g019-q11.html"
  #url = "https://item.rakuten.co.jp/tsuruyagolf/0136200086/"
  #url = "https://item.rakuten.co.jp/alpen/0116550027/"
  url = "https://en.zalando.de/tommy-hilfiger-day-dress-red-to121c0jt-t11.html"
  #url = "https://item.rakuten.co.jp/firststage/2020020110h/"
  web_manager.load(url)
  
  try:
    #For zalando
    web_manager.click_elements("//*[@id='picker-trigger']")
    time.sleep(3)
    web_manager.build_lxml_tree()

    print('Crawling option name')
    #For rakuten
    #option_names = web_manager.get_values_by_lxml("//td[@class='floating-cart-options-table']//span[contains(@class,'choiceText')]",'alltext')
    #option_names = web_manager.get_values_by_lxml("//td[position() mod 2 = 1]/span[@class='inventory_title']",'alltext')
    #print(option_names)

    #For zalando
    option_names = web_manager.get_values_by_lxml("//*[@id='picker-trigger']/span/span",'alltext')

    #//tr[1]/td[@class='inventory_choice_name']//span 
    #//tr[position()>1]/td[@class='inventory_choice_name']//span

    print('Crawling option values')
    #For rakuten
    #option_values = web_manager.get_option_values_by_lxml("//td[@class='floating-cart-options-table']//select[@name='choice']", "./option", 'alltext')


    #option_x_value = web_manager.get_values_by_lxml("//tr[1]/td[@class='inventory_choice_name']//span",'alltext')
    #option_y_value = web_manager.get_values_by_lxml("//tr[position()>1]/td[@class='inventory_choice_name']//span",'alltext')

    #option_combination_value = web_manager.get_values_by_lxml("//td[@class='inventory']/span[@class='inventory_soldout'] | //input[@name='inventory_id']",'alltext')
    #//td[@class='inventory'] (row-wise)
    #For zalando
    option_values = web_manager.get_option_values_by_lxml("/html/body//div/div/div[3]/div/form/div", "./div/div/label/span/div/span[1]", 'alltext')
    print(option_values)
    option_values = web_manager.get_option_values_by_lxml("/html/body//div/div/div[3]/div/form/div", "./div/div/label", 'alltext')
    print(option_values)
    #res = {}
    #for idx, option_name in enumerate(option_names):
    #  res[option_name] = option_values[idx]

    res = {}
    #for idx, option_name in enumerate(option_names):
    #  print(idx)
    #  if idx == 0:
    #    res[option_name] = option_x_value
    #  elif idx == 1:
    #    res[option_name] = option_y_value
  
    #res['option_matrix_row_wise_value'] = option_combination_value 
    
    #print('---------------------------------------')
    #print(res)
    #print('---------------------------------------')
    #for key in res.keys():
    #  print('Option name: ', key)
    #  print('Option values: ', res[key])
    #  print('\n')
  except:
    print(str(traceback.format_exc()))
    pass 
  web_manager.close()

  ##def interceptor(request):
  ##    request.method = 'POST'
  ##web_manager.get_cur_driver_().request_interceptor = interceptor
  ##sleep_time = 1000
  ##cnt = 0
  #print('loop')
  #while True:
  #  try:
  #    web_manager.load('https://www.amazon.com/ref=nav_logo')
  #    time.sleep(1)
  #    chaptcha_xpath = '//input[@id=\'captchacharacters\']' # for amazon
  #    print('Check captcha')
  #    check_chaptcha = web_manager.get_elements_by_selenium_(chaptcha_xpath)
  #    if len(check_chaptcha) != 0:
  #      raise
  #    print('request other url')
  #    web_manager.load('https://www.amazon.com/s?rh=n%3A21606832011&s=featured-rank&pd_rd_r=c59ecd00-2a14-48a3-bcce-a677ba6d08a8&pd_rd_w=ciUrC&pd_rd_wg=GwxYY&pf_rd_p=d6a73408-22a8-41b0-a103-02acc979f47b&pf_rd_r=TBM29BHHWXPCS3BBXKZX&ref=pw_gw_prime_topquadcard_apr_m_stylestaples')
  #    time.sleep(5)
  #  except:
  #    print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
  #    print('Except')
  #    pass
  #    break;

  #link = web_manager.get_value_by_selenium('//form[@action="/errors/validateCaptcha"]//img', 'src')
  #print('link = {}'.format(link))
  #captcha = AmazonCaptcha.fromlink(link)
  #solution = captcha.solve()
  #print('solution = {}'.format(solution))
  #web_manager.send_keys_to_elements('//input[@id="captchacharacters"]',solution)
  #web_manager.click_elements('//button')
  #print("sleep {}s".format('5'))
  #time.sleep(5)
  #print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
  #try:
  #  print(web_manager.get_value_by_selenium('//*[@id="glow-ingress-line2"]', "alltext"))
  #except:
  #  pass
  #web_manager.load(url)
  #print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
  #print(web_manager.get_value_by_selenium('//*[@id="glow-ingress-line2"]', "alltext"))
  

### 
#    url = 'http://www.amazon.com/gp/delivery/ajax/address-change.html?locationType=LOCATION_INPUT&zipCode=94024&storeContext=office-products&deviceType=web&pageType=Detail&actionSource=glow&almBrandId=undefined'
#    def interceptor2(request):
#        del request.headers['anti-csrftoken-a2z']
#        request.headers['anti-csrftoken-a2z'] = token 
#    web_manager.get_cur_driver_().request_interceptor = interceptor2 
#    cnt = 0
#    while True:
#      try:
#        web_manager.load(url)
#        print('"isValidAddress":1' in web_manager.get_html())
#        if '"isValidAddress":1' in web_manager.get_html():
#          break;
#        else:
#          raise
#      except:
#        sleep_time = sleep_time + int(random.randrange(1,61)) 
#        print("sleep {}s".format(sleep_time))
#        time.sleep(sleep_time)
#        cnt = cnt + 1
#        if cnt >= 2:
#          print('RRRRRRRRestart')
#          web_manager.restart(5)
#          def interceptor4(request):
#            del request.headers['anti-csrftoken-a2z']
#            request.headers['anti-csrftoken-a2z'] = token 
#          web_manager.get_cur_driver_().request_interceptor = interceptor4
#          cnt = 0
#        pass
#
#    def interceptor3(request):
#        request.method = 'GET'
#
#    web_manager.load('http://www.amazon.com')
#    print(web_manager.get_value_by_selenium('//*[@id="glow-ingress-line2"]', "alltext"))
#  web_manager.close()
#
