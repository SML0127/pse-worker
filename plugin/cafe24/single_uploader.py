import sys
import os
import json
import base64
import requests
import psycopg2
import subprocess
import traceback
import pprint
import time
import re
import itertools

from flask import Flask
from flask_restful import Resource, Api
from flask_restful import reqparse
from flask_cors import CORS


from price_parser import Price
from forex_python.converter import CurrencyRates


from plugin.cafe24.APIManagers import Cafe24Manager
from managers.graph_manager import GraphManager
from managers.settings_manager import *
from engine.exporter import Exporter

from multiprocessing.dummy import Pool as ThreadPool
from functools import partial
print_flushed = partial(print, flush=True)


class Cafe24SingleUploader(Resource):

  def __init__(self):
    self.setting_manager = SettingsManager()
    self.setting_manager.setting("/home/pse/PSE-engine/settings-worker.yaml")
    self.settings = self.setting_manager.get_settings()
    self.cafe24manager = ''
    self.graph_manager = ''
    self.exporter = ''
    pass


  def upload_products_of_mpid(self, args, mpids):
    total_time = time.time()
    profiling_info = {}
    try:
      num_threads = args.get('num_threads', 1)
      #pool = ThreadPool(num_threads)
      print_flushed('num threads in args: ', num_threads)
      self.graph_manager = GraphManager()
      self.graph_manager.init(self.settings)

      #exec_id = args['execution_id']
      #args['job_id'] = self.graph_manager.get_job_id_from_eid(exec_id)

      chunk_size = (len(mpids) // num_threads) + 1
      mpid_chunks = [mpids[i:i + chunk_size] for i in range(0, len(mpids), chunk_size)]
      tasks = []
      for i in range(len(mpid_chunks)):
        nargs = args.copy()
        nargs.update(args['clients'][i])
        tasks.append((nargs, mpid_chunks[i]))
      #tasks = list(map(lambda x: (args.copy(), x), mpid_chunks))
      #results = pool.map(self.upload_products_of_task_from_mpid, tasks)
      results = self.upload_products_of_task_from_mpid(tasks[0])
      profiling_info['threads'] = results
    except:
      profiling_info['total_time'] = time.time() - total_time
      #print_flushed(traceback.format_exc())
      #pool.close()
      #pool.join()
      
      self.graph_manager.disconnect()
      #print_flushed(profiling_info)
      return profiling_info
    profiling_info['total_time'] = time.time() - total_time
    #print_flushed(profiling_info)
    #pool.close()
    #pool.join()
    self.graph_manager.disconnect()
    return profiling_info


  def upload_products_of_task_from_mpid(self, task):
    total_time = time.time()
    successful_node = 0
    failed_node = 0
    profiling_info = {}
    log_mpid = -1
    log_mt_history_id = -1
    log_max_num_product = 0
    err_cafe24_op = 'Init cafe24 configuration'
    log_mpids = []
    log_mpids_array = []
    targetsite_url = ""
    job_id = -1 
    try:
      (args, mpids) = task
      job_id = args['job_id'] 
      log_mt_history_id = args['mt_history_id']
      log_max_num_product = len(mpids)
      log_mpids_array = mpids
      log_mpids = ', '.join(map(str, mpids)) 

      self.exporter = Exporter()
      self.exporter.init()
      err_cafe24_op = 'Import transformation program'
      self.exporter.import_rules_from_code(args['code'])

      self.cafe24manager = Cafe24Manager(args)
      print_flushed("-----------------------Request auth code----------------------")
      err_cafe24_op = 'Get cafe24 auth code'
      self.cafe24manager.get_auth_code(log_mt_history_id)
      print_flushed("-----------------------Request token--------------------------")
      err_cafe24_op = 'Get cafe24 token'
      self.cafe24manager.get_token()
      self.cafe24manager.list_brands()
      #targetsite_url = 'https://{}.cafe24.com/'.format(args['mall_id'])


      #print_flushed(exec_id, label)
      #print_flushed(node_ids)
      tsid = args['tsid'] 
      targetsite_url, gateway = self.graph_manager.get_targetsite(tsid)
      print_flushed("tsid: ", tsid)
      print_flushed("targetsite: ", targetsite_url)
      if 'selected' in args:
        for mpid in mpids:
          log_mpid = mpid
          node_time = time.time()
          try:
            product, original_product_information = self.exporter.export_from_selected_mpid(job_id, args['execution_id'], mpid)
            product['targetsite_url'] = targetsite_url
            product['mpid'] = mpid
            status = self.graph_manager.check_status_of_product(job_id, mpid)
             
            #Status 0 = up to date, 1 = changed, 2 = New, 3 = Deleted 4 = Duplicated
            print_flushed('status : ', status)
            if gateway.upper() == 'CAFE24':
              tpid = self.graph_manager.get_tpid(job_id, targetsite_url, mpid)
              self.cafe24manager.update_exist_product(product, profiling_info, job_id, tpid, log_mt_history_id)
              self.cafe24manager.refresh()
            cnum  = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
            #smlee
            try:
              self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, original_product_information, product, targetsite_url, cnum, status) 
            except:
              self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
              pass 

          except Exception as e:
            failed_node += 1
            err_msg = '================================ Operator ================================ \n'
            err_msg += 'Update exist product \n\n'
            err_msg += '================================ My site product id ================================ \n'
            err_msg += 'My site product id: ' + str(log_mpid) + '\n\n'
            err_msg += '================================ Target site URL ================================ \n'
            err_msg += 'URL: ' + targetsite_url + '\n\n'
            err_msg += '================================ Error Message ================================ \n'
            err_msg += str(e) + '\n\n'
            err_msg += '================================ STACK TRACE ============================== \n' + str(traceback.format_exc())
            self.graph_manager.log_err_msg_of_upload(log_mpid, err_msg, log_mt_history_id )
            status = self.graph_manager.check_status_of_product(job_id, log_mpid)
            self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], log_mpid,{'Error':'Set-up error (before upload)'},{'Error':'Set-up error (before upload)'}, targetsite_url, -1, status) 
          finally:
            self.graph_manager.log_expected_num_target_success(log_mt_history_id, 1, args['targetsite_encode'])
          successful_node += 1

      elif 'onetime' in args:
        for mpid in mpids:
          log_mpid = mpid
          node_time = time.time()
          log_operation = ''
          try:
            status = self.graph_manager.check_status_of_product(job_id, mpid)
             
            #Status 0 = up to date, 1 = changed, 2 = New, 3 = Deleted 4 = Duplicated
            print_flushed('status : ', status)
            if gateway.upper() == 'CAFE24':
              is_uploaded = self.graph_manager.check_is_item_uploaded(job_id, targetsite_url, mpid)
              print_flushed('is uploaded proudct? : ', is_uploaded)
              if is_uploaded == False and status != 3: # upload as new item
                product, original_product_information = self.exporter.export_from_mpid_onetime(job_id, mpid, tsid)
                log_operation = 'Create new product'
                product['targetsite_url'] = targetsite_url
                product['mpid'] = mpid
                print_flushed('mpid : ', mpid)
                self.cafe24manager.upload_new_product(product, profiling_info, job_id, log_mt_history_id)
                cnum = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                #smlee
                try:
                  self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, original_product_information, product, targetsite_url, cnum, status) 
                except:
                  self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                  pass 

              elif is_uploaded == True:
                if status == 1:
                  product, original_product_information = self.exporter.export_from_mpid_onetime(job_id, mpid, tsid)
                  log_operation = 'Update exist product'
                  product['targetsite_url'] = targetsite_url
                  product['mpid'] = mpid
                  tpid = self.graph_manager.get_tpid(job_id, targetsite_url, mpid)
                  print_flushed('mpid : ', mpid)
                  print_flushed('tpid : ', tpid)
                  self.cafe24manager.update_exist_product(product, profiling_info, job_id, tpid, log_mt_history_id)
                  cnum = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                  #smlee
                  try:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, original_product_information, product, targetsite_url, cnum, status) 
                  except:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                    pass 
                elif status == 0:
                  try:
                    cnum = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, {'status':'0', 'name':'Up-to-date (Do not update)'}, {'status':'3', 'name':'Up-to-date (Do not update)'}, targetsite_url, cnum, status) 
                  except:
                    cnum = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                    pass 

                elif status == 3:
                  tpid = self.graph_manager.get_tpid(job_id, targetsite_url, mpid)
                  print_flushed('Delete tpid : ', tpid)
                  print_flushed('Delete mpid : ', mpid)
                  log_operation = 'Delete product'
                  self.cafe24manager.hide_exist_product(profiling_info, job_id, tpid)
                  cnum  = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                  #smlee
                  try:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, {'status':'3', 'name':'Deleted', 'stock': 0}, {'status':'3', 'name':'Deleted', 'stock': 0}, targetsite_url, cnum, status) 
                  except:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                    pass 

              self.cafe24manager.refresh()
            successful_node += 1
          except:
            failed_node += 1     
            err_msg = '================================ Operator ================================ \n'
            err_msg += log_operation +'\n\n'
            err_msg += '================================ My site product id ================================ \n'
            err_msg += 'My site product id: ' + str(log_mpid) + '\n\n'
            err_msg += '================================ Target site URL ================================ \n'
            err_msg += 'URL: ' + targetsite_url + '\n\n'
            err_msg += '================================ STACK TRACE ============================== \n' + str(traceback.format_exc())
            self.graph_manager.log_err_msg_of_upload(log_mpid, err_msg, log_mt_history_id )
            try:
              status = self.graph_manager.check_status_of_product(job_id, log_mpid)
              self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], log_mpid,{'Error':'Set-up error (before upload)'},{'Error':'Set-up error (before upload)'}, targetsite_url, -1, status) 
            except:
              print(str(traceback.format_exc()))
          finally:
            self.graph_manager.log_expected_num_target_success(log_mt_history_id, 1, args['targetsite_encode'])
            
      else:
        for mpid in mpids:
          log_mpid = mpid
          node_time = time.time()
          log_operation = ''
          try:
            status = self.graph_manager.check_status_of_product(job_id, mpid)
            #Status 0 = up to date, 1 = changed, 2 = New, 3 = Deleted 4 = Duplicated
            print_flushed('status : ', status)
            if gateway.upper() == 'CAFE24':
              is_uploaded = self.graph_manager.check_is_item_uploaded(job_id, targetsite_url, mpid)
              print_flushed('is uploaded proudct? : ', is_uploaded)
              if is_uploaded == False and status != 3: # upload as new item
                product, original_product_information = self.exporter.export_from_mpid_onetime(job_id, mpid, tsid)
                product['targetsite_url'] = targetsite_url
                product['mpid'] = mpid
                print_flushed('mpid : ', mpid)
                log_operation = 'Create new product'
                self.cafe24manager.upload_new_product(product, profiling_info, job_id, log_mt_history_id)
                cnum  = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                #smlee
                try:
                  self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, original_product_information, product, targetsite_url, cnum, status) 
                except:
                  self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                  pass
 
              elif is_uploaded == True:
                if status == 1:
                  product, original_product_information = self.exporter.export_from_mpid_onetime(job_id, mpid, tsid)
                  product['targetsite_url'] = targetsite_url
                  product['mpid'] = mpid
                  log_operation = 'Update exist product'
                  print_flushed('mpid : ', mpid)
                  tpid = self.graph_manager.get_tpid(job_id, targetsite_url, mpid)
                  self.cafe24manager.update_exist_product(product, profiling_info, job_id, tpid, log_mt_history_id)
                  cnum  = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                  #smlee
                  try:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, original_product_information, product, targetsite_url, cnum, status) 
                  except:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                    pass
                elif status == 0:
                  try:
                    cnum = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, {'status':'0', 'name':'Up-to-date (Do not update)'}, {'status':'3', 'name':'Up-to-date (Do not update)'}, targetsite_url, cnum, status) 
                  except:
                    cnum = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                    pass
 
                elif status == 3:
                  tpid = self.graph_manager.get_tpid(job_id, targetsite_url, mpid)
                  print_flushed('Delete tpid : ', tpid)
                  print_flushed('Delete mpid : ', mpid)
                  log_operation = 'Delete product'
                  self.cafe24manager.hide_exist_product(profiling_info, job_id, tpid)
                  cnum = self.graph_manager.get_cnum_from_targetsite_job_configuration_using_tsid(tsid)
                  #smlee
                  try:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid, {'status':'3', 'name':'Deleted', 'stock': 0}, {'status':'3', 'name':'Deleted', 'stock': 0}, targetsite_url, cnum, status) 
                  except:
                    self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Logging error'},{'Error':'Logging error'}, targetsite_url, cnum, status) 
                    pass 

              self.cafe24manager.refresh()

            successful_node += 1
          except Exception as e:
            failed_node += 1
            err_msg = '================================ Operator ================================ \n'
            err_msg += log_operation +'\n\n'
            err_msg += '================================ My site product id ================================ \n'
            err_msg += 'My site product id: ' + str(log_mpid) + '\n\n'
            err_msg += '================================ Target site URL ================================ \n'
            err_msg += 'URL: ' + targetsite_url + '\n\n'
            err_msg += '================================ Error Message ================================ \n'
            err_msg += str(e) + '\n\n'
            err_msg += '================================ STACK TRACE ============================== \n' + str(traceback.format_exc())
            self.graph_manager.log_err_msg_of_upload(log_mpid, err_msg, log_mt_history_id )
            status = self.graph_manager.check_status_of_product(job_id, log_mpid)
            self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], log_mpid,{'Error':'Set-up error (before upload)'},{'Error':'Set-up error (before upload)'}, targetsite_url, -1, status) 
          finally:
            self.graph_manager.log_expected_num_target_success(log_mt_history_id, 1, args['targetsite_encode'])

      self.cafe24manager.close()
      self.exporter.close()
      print_flushed("Close cafe24 manager (no except)")
    except:
      try:
        failed_node = log_max_num_product
        err_msg = "Fail to upload items \n"
        err_msg += err_cafe24_op + " \n"
        err_msg += "My site product pids: " + log_mpids + " \n" 
        err_msg += '================================ STACK TRACE ============================== \n' + str(traceback.format_exc())
        self.graph_manager.log_err_msg_of_upload(-1, err_msg, log_mt_history_id )
        
        profiling_info['total_time'] = time.time() - total_time
        profiling_info['successful_node'] = 0
        profiling_info['failed_node'] = failed_node
        print_flushed('s/f', successful_node, '/', failed_node)
        print_flushed(traceback.format_exc())
        for mpid in log_mpids_array:
          try:
            status = self.graph_manager.check_status_of_product(job_id, mpid)
            self.graph_manager.logging_all_uploaded_product(log_mt_history_id, job_id, args['execution_id'], mpid,{'Error':'Set-up error (before upload)'},{'Error':'Set-up error (before upload)'}, targetsite_url, -1, status) 
            err_msg = "Set-up error (e.g. get authorization, get token ...) \n"
            err_msg += "?????? ?????? ID: " + str(mpid) + " \n" 
            err_msg += '================================ STACK TRACE ============================== \n' + str(traceback.format_exc())
            self.graph_manager.log_err_msg_of_upload(mpid, err_msg, log_mt_history_id )
          except:
            print_flushed(traceback.format_exc())
        self.graph_manager.log_expected_num_target_success(log_mt_history_id, failed_node, args['targetsite_encode'])
      except:
        print_flushed(traceback.format_exc())
        
      try:
         self.cafe24manager.close()
      except:
         print_flushed("Error in close cafe24 manager")
         print_flushed(traceback.format_exc())
      try:
         self.exporter.close()
      except:
         print_flushed("Error in close exporter")
         print_flushed(traceback.format_exc())
      print_flushed("Close cafe24 manager (in except)")
      return profiling_info
    print_flushed('s/f', successful_node, '/', failed_node)
    profiling_info['total_time'] = time.time() - total_time
    profiling_info['successful_node'] = successful_node
    profiling_info['failed_node'] = failed_node
    #print_flushed(profiling_info)
    return profiling_info

  # smlee
  def close(self):
    try:
      self.cafe24manager.close()
      self.exporter.close()
      self.graph_manager.disconnect()
    except:
      pass

  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('req_type')
    parser.add_argument('mall_id')
    parser.add_argument('user_id')
    parser.add_argument('user_pwd')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('redirect_uri')
    parser.add_argument('scope')
    parser.add_argument('execution_id')
    parser.add_argument('transform_id')
    #parser.add_argument('transformations')
    args = parser.parse_args()
    if args['req_type'] == 'upload_products': 
      return self.upload_products(args)
      #return self.upload_products_of_execution(args)
    elif args['req_type'] == "run_upload_driver":
      return self.run_upload_driver(args)
    return {}


app = Flask(__name__)
api = Api(app)
api.add_resource(Cafe24SingleUploader, '/upload/cafe24')

if __name__ == '__main__':
  cafe24api = Cafe24SingleUploader()
  args = {}
  args['execution_id'] = 649
  args['label'] = 7
  args['clients'] = [
      {'client_id': 'oc4Eair8IB7hToJuyjJsiA', 'client_secret': 'EMsUrt4tI1zgSt2i3icPPC'},
      {'client_id': 'lmnl9eLRBye5aZvfSU4tXE', 'client_secret': 'nKAquRGpPVsgo6GZkeniLA'},
      {'client_id': 'Vw9ygiIAJJLnLDKiAkhsDA', 'client_secret': 'p6EqNWe8DqEHRtxyzP4S4D'},
      {'client_id': 'UyLmMdVBOJHvYy0VF4pcpA', 'client_secret': 'dy2CzhMiK9OrLMHyIq37mC'},
      {'client_id': 'AafM42MiBie2mB3mRMM0bE', 'client_secret': 'Lv3S8HfvZCxdXifxfb2QMP'},
      {'client_id': 'f8rDSAXoWiwPPIBchadCfH', 'client_secret': 'f1yQdvaSN6OLD19qJ1m7oD'},
      {'client_id': 'nj0kecRmH6IEn0zFZecHZM', 'client_secret': 'xJ4a9htZGhogr1H2mZNibB'},
      {'client_id': 'nP5GWlrOER7kbYVu6QEtGA', 'client_secret': 'mctijmPmOp8lKOaex0VlLF'},
      {'client_id': 'LkgQ03ETLtTiCRfmYa5dgD', 'client_secret': '49XJnilLP96vlcKWu8zr8A'},
      {'client_id': 'ZIfFO0T6HSHZX4QPpf86EF', 'client_secret': 'oqUEjpMBONgiRMmyE4zAvA'},
      {'client_id': 'fDhrr2B1DyQEvuaHUPUD1D', 'client_secret': 'WyCr0qkfHKWWZlWl8fcxiK'},
      {'client_id': 'K0JPoImnDJXn8giYecK5yE', 'client_secret': 'TaW51jMeHaZTLveIjfhXe2'},
      {'client_id': 'UzhOkGW6H5An6QaYpfMHQA', 'client_secret': 'swcXg2pEFVFjdBanSUfqaC'},
      {'client_id': 'ojrikKQeGiBcVkUBybQGYB', 'client_secret': 'zHdUFOUSHZUkRV4QJdoRvD'},
      {'client_id': 'avZzMvjjCx4mNz8OOKLjcB', 'client_secret': 'H2OTer0OIi3WZyvS7gYeiP'},
      {'client_id': 'ehLMLKGobqVOxsoYgu5W1E', 'client_secret': 'tTWPLjC9IdCp9sMK0j4JKD'}
    ]
  f = open('./cafe24_zalando.py')
  args['code'] = f.read()
  f.close()
  args['mall_id'] = 'mallmalljmjm'
  args['user_id'] = 'mallmalljmjm'
  args['user_pwd'] = 'Dlwjdgns2'
  args['redirect_uri'] = 'https://www.google.com'
  args['scope'] = 'mall.write_product mall.read_product mall.read_category mall.write_category mall.read_collection mall.write_collection'
  cafe24api.upload_products(args)
  #app.run(debug=True, host='0.0.0.0', port=5002) 
