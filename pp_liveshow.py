import os
import copy
from Tkinter import *
import Tkinter as tk
import PIL.Image
import PIL.ImageTk
import PIL.ImageEnhance

from pp_imageplayer import ImagePlayer
from pp_videoplayer import VideoPlayer
from pp_medialist import MediaList
from pp_utils import Monitor
from pp_messageplayer import MessagePlayer
from pp_options import command_options
from pp_resourcereader import ResourceReader


class LiveShow:


    NEW_TRACKS={'image':{'title':'New Image','track-ref':'','type':'image','location':'','duration':'','transition':'',
                              'track-text':'','track-text-font':'','track-text-colour':'','track-text-x':'0','track-text-y':'0'},
                'video':{'title':'New Video','track-ref':'','type':'video','location':'','omx-audio':''}}
    
    IMAGE_FILES=('.gif','.jpg','.jpeg','.bmp','.png','.tif')
    VIDEO_FILES=('.mp4','.mkv','.avi','.mp2','.wmv', '.vob')
    AUDIO_FILES=('.mp3','.wav','.ogg')
                         
# *******************
# External interface
# ********************

    def __init__(self,
                            show,
                            canvas,
                            showlist,
                            pp_home,
                            pp_profile):
        """ canvas - the canvas that the show is to be written on
            showlist - used jus to check the issue of medialist against showlist
            show - the dictionary for the show to be played
            pp_home - Pi presents data_home directory
            pp_profile - Pi presents profile directory
        """

        self.mon=Monitor()
        self.mon.on()
        
        #instantiate arguments
        self.show =show
        self.showlist=showlist
        self.canvas=canvas
        self.pp_home=pp_home
        self.pp_profile=pp_profile

        # open resources
        self.rr=ResourceReader()

        # Init variables
        self.player=None
        self.shower=None
        self._end_liveshow_signal=False
        self._play_child_signal = False
        self.error=False
        
        self._livelist=None
        self._new_livelist= None


    def play(self,end_callback,ready_callback=None, top=False,command='nil'):

        """ displays the liveshow
              end_callback - function to be called when the liveshow exits
              ready_callback - callback when liveshow is ready to display
              top is True when the show is top level (i.e. run from start show)
        """

        #instantiate the arguments
        self._end_callback=end_callback
        self._ready_callback=ready_callback
        self.top=top
        self.mon.log(self,"Starting show: " + self.show['show-ref'])

        # check  data files are available.
        self.media_file = self.pp_profile + os.sep + self.show['medialist']
        if not os.path.exists(self.media_file):
            self.mon.err(self,"Medialist file not found: "+ self.media_file)
            self._stop("Medialist file not found")
            
        self.options=command_options()
               
        self._pp_live_dir1 = self.pp_home + os.sep + 'pp_live_tracks'
        if not os.path.exists(self._pp_live_dir1):
            os.mkdir(self._pp_live_dir1)

        self._pp_live_dir2=''   
        if self.options['liveshow'] <>"":
            self._pp_live_dir2 = self.options['liveshow']
            if not os.path.exists(self._pp_live_dir2):
                self.mon.err(self,"live tracks directory not found " + self._pp_live_dir2)
                self._end('error',"live tracks directory not found")

        #create a medialist for the liveshow and read it.
        # it should be empty of anonymous tracks but read it to check its version.
        self.medialist=MediaList()
        if self.medialist.open_list(self.media_file,self.showlist.sissue())==False:
            self.mon.err(self,"Version of medialist different to Pi Presents")
            self._end('error',"Version of medialist different to Pi Presents")
        
        if self.ready_callback<>None:
             self.ready_callback()
             
        self._play_first_track()
        
 


   # respond to key presses.
    def key_pressed(self,key_name):
        self.mon.log(self,"received key: " + key_name)
        
        if key_name=='':
            pass
        
        elif key_name=='escape':
            # if next lower show eor player is running pass down to stop the show/track
            # ELSE stop this show except for exceptions
            if self.shower<>None:
                self.shower.key_pressed(key_name)
            elif self.player<>None:
                self.player.key_pressed(key_name)
            else:
                # not at top so stop the show
                if  self.top == False:
                    self._stop("exit show to higher level")
                else:
                    pass
    
        elif key_name in ('up','down'):
        # if child or sub-show is running and is a show pass to show, track does not use up/down
            if self.shower<>None:
                self.shower.key_pressed(key_name)

                
        elif key_name=='return':
            # if child show or sub-show is running and is show - pass down
            # ELSE use Return to start child
            if self.shower<>None:
                self.shower.key_pressed(key_name)
            else:
                if self.show['has-child']=="yes":
                    self._play_child()
              
        elif key_name in ('p',' '):
            # pass down if show or track running.
            if self.shower<>None:
                self.shower.key_pressed(key_name)
            elif self.player<>None:
                self.player.key_pressed(key_name)
 

    def button_pressed(self,button,edge):
        if button=='play': self.key_pressed("return")
        elif  button =='up': self.key_pressed("up")
        elif button=='down': self.key_pressed("down")
        elif button=='stop': self.key_pressed("escape")
        elif button=='pause': self.key_pressed('p')


       
    # kill or error
    def terminate(self,reason):
        if self.shower<>None:
            self.mon.log(self,"sent terminate to shower")
            self.shower.terminate(reason)
        elif self.player<>None:
            self.mon.log(self,"sent terminate to player")
            self.player.terminate(reason)
        else:
            self._end(reason,'terminated without terminating shower or player')

 
    def _tidy_up(self):
        pass


    def resource(self,section,item):
        value=self.rr.get(section,item)
        if value==False:
            self.mon.err(self, "resource: "+section +': '+ item + " not found" )
            self.terminate("error",'Cannot find resource')
        else:
            return value
        

# ***************************
# Respond to key/button presses
# ***************************

    def _stop(self,message):
        self._end_liveshow_signal=True

        
    def _play_child(self):
        self._play_child_signal=True
        if self.player<>None:
            self.player.key_pressed("escape")
      
        
# ***************************
# end of show functions
# ***************************

    def _end(self,reason,message):
        self._end_liveshow_signal=False
        self.mon.log(self,"Ending Liveshow: "+ self.show['show-ref'])
        self._tidy_up()
        self._end_callback(reason,message)
        self=None
        return
        
    def _nend(self):
        self._end('normal','end from state machine')
  

# ***************************
# Livelist
# ***************************       
        
    def _livelist_add_track(self,afile):
        (root,title)=os.path.split(afile)
        (root,ext)= os.path.splitext(afile)
        if ext.lower() in LiveShow.IMAGE_FILES:
            self._livelist_new_track(LiveShow.NEW_TRACKS['image'],{'title':title,'track-ref':'','location':afile})
        if ext.lower() in LiveShow.VIDEO_FILES:
            self._livelist_new_track(LiveShow.NEW_TRACKS['video'],{'title':title,'track-ref':'','location':afile})
        if ext.lower() in LiveShow.AUDIO_FILES:
            self._livelist_new_track(LiveShow.NEW_TRACKS['video'],{'title':title,'track-ref':'','location':afile})
           


        
    def _livelist_new_track(self,fields,values):
        new_track=fields
        self._new_livelist.append(copy.deepcopy(new_track))
        last = len(self._new_livelist)-1
        self._new_livelist[last].update(values)        
    

        
    def _new_livelist_create(self):
     
        self._new_livelist=[]
        if os.path.exists(self._pp_live_dir1):
            for file in os.listdir(self._pp_live_dir1):
                file = self._pp_live_dir1 + os.sep + file
                (root_file,ext_file)= os.path.splitext(file)
                if ext_file.lower() in LiveShow.IMAGE_FILES+LiveShow.VIDEO_FILES+LiveShow.AUDIO_FILES:
                    self._livelist_add_track(file)
                    
        if os.path.exists(self._pp_live_dir2):
            for file in os.listdir(self._pp_live_dir2):
                file = self._pp_live_dir2 + os.sep + file
                (root_file,ext_file)= os.path.splitext(file)
                if ext_file.lower() in LiveShow.IMAGE_FILES+LiveShow.VIDEO_FILES+LiveShow.AUDIO_FILES:
                    self._livelist_add_track(file)
                    

        self._new_livelist= sorted(self._new_livelist, key= lambda track: os.path.basename(track['location']).lower())
#       for it in self._new_livelist:
#          print it['location']
#      print ''


    
    def _livelist_replace_if_changed(self):
        self._new_livelist_create()
        if  self._new_livelist<>self._livelist:
            self._livelist=copy.deepcopy(self._new_livelist)
            self._livelist_index=0
   
   
    def _livelist_next(self):
        if self._livelist_index== len(self._livelist)-1:
            self._livelist_index=0
        else:
            self._livelist_index +=1


# ***************************
# Play Loop
# ***************************
 
    def _play_first_track(self):
        self._new_livelist_create()
        self._livelist = copy.deepcopy(self._new_livelist)
        self._livelist_index = 0
        self._play_track()

        
    def _play_track(self):        
        self._livelist_replace_if_changed()
        if len(self._livelist)>0:
            self._play_selected_track(self._livelist[self._livelist_index])
        else:
            self.display_message(self.canvas,None,self.resource('liveshow','m01'),5,self._what_next)
     
    def _what_next(self):   
        # user wants to end 
        if self._end_liveshow_signal==True:
            self._end_liveshow_signal=False
            self._end('normal',"show ended by user")
        
        # play child?
        elif self._play_child_signal == True:
            self._play_child_signal=False
            index = self.medialist.index_of_track('pp-child-show')
            if index >=0:
                #don't select the track as need to preserve mediashow sequence.
                child_track=self.medialist.track(index)
                self._display_eggtimer(self.resource('liveshow','m02'))
                self._play_selected_track(child_track)
            else:
                self.mon.err(self,"Child show not found in medialist: "+ self.show['pp-child-show'])
                self._end('error',"child show not found in medialist")
                
        # otherwise loop to next track                       
        else:
            self._livelist_next()
            self._play_track()
          
      
# ***************************
# Dispatching to Players/Shows 
# ***************************

    # used to display internal messages in situations where a medialist entry could not be used.
    def display_message(self,canvas,source,content,duration,_display_message_callback):
            self._display_message_callback=_display_message_callback
            tp={'duration':duration,'message-colour':'white','message-font':'Helvetica 20 bold'}
            self.player=MessagePlayer(canvas,tp,tp)
            self.player.play(content,self._display_message_end,None)

            
    def  _display_message_end(self,reason,message):
        self.player=None
        if reason in ("killed",'error'):
            self._end(reason,message)
        else:
            self._display_message_callback()


    def complete_path(self,selected_track):
        #  complete path of the filename of the selected entry
        track_file = selected_track['location']
        if track_file[0]=="+":
                track_file=self.pp_home+track_file[1:]
        self.mon.log(self,"Track to play is: "+ track_file)
        return track_file     
         

    def _play_selected_track(self,selected_track):
        """ selects the appropriate player from type field of the medialist and computes
              the parameters for that type
              selected_track is a dictionary for the track/show
        """
        # self.canvas.delete(ALL)
        
        # is menu required
        if self.show['has-child']=="yes":
            enable_child=True
        else:
            enable_child=False

        #dispatch track by type
        self.player=None
        self.shower=None
        track_type = selected_track['type']
        self.mon.log(self,"Track type is: "+ track_type)
                                      
        if track_type=="image":
            track_file=self.complete_path(selected_track)
            # images played from menus don't have children
            self.player=ImagePlayer(self.canvas,self.show,selected_track)
            self.player.play(track_file,
                                    self.end_player,
                                    self.ready_callback,
                                    enable_menu=enable_child)
        elif track_type=="video":
            # create a videoplayer
            track_file=self.complete_path(selected_track)
            self.player=VideoPlayer(self.canvas,self.show,selected_track)
            self.player.play(track_file,
                                        self.end_player,
                                        self.ready_callback,
                                        enable_menu=enable_child)
            
        elif track_type=="show":
            # get the show from the showlist
            index = self.showlist.index_of_show(selected_track['sub-show'])
            if index >=0:
                self.showlist.select(index)
                selected_show=self.showlist.selected_show()
            else:
                self.mon.err(self,"Show not found in showlist: "+ selected_track['sub-show'])
                self._stop("Unknown show")
                
            if selected_show['type']=="mediashow":    
                self.shower= MediaShow(selected_show,
                                                                self.canvas,
                                                                self.showlist,
                                                                self.pp_home,
                                                                self.pp_profile)
                self.shower.play(self.end_shower,top=False,command='nil')

            
            elif selected_show['type']=="menu":
                self.shower= MenuShow(selected_show,
                                                        self.canvas,
                                                        self.showlist,
                                                        self.pp_home,
                                                        self.pp_profile)
                self.shower.play(self.end_shower,top=False,command='nil')
                
            else:
                self.mon.err(self,"Unknown Show Type: "+ selected_show['type'])
                self._stop("Unknown show type")  
                                                                            
        else:
            self.mon.err(self,"Unknown Track Type: "+ track_type)
            self._stop("Unknown track type")            


    def ready_callback(self):
        self._delete_eggtimer()
        
        
    def end_player(self,reason,message):
        self.mon.log(self,"Returned from player with message: "+ message)
        self.player=None
        if reason in("killed","error"):
            self._end(reason,message)
        else:
            self._what_next()

    def end_shower(self,reason,message):
        self.mon.log(self,"Returned from shower with message: "+ message)
        self.shower=None
        if reason in("killed","error"):
            self._end(reason,message)
        else:
            self._what_next()  
        
        
    def _display_eggtimer(self,text):
        self.canvas.create_text(int(self.canvas['width'])/2,
                                              int(self.canvas['height'])/2,
                                                  text= text,
                                                  fill='white',
                                                  font="Helvetica 20 bold")
        self.canvas.update_idletasks( )


    def _delete_eggtimer(self):
            self.canvas.delete(ALL)
        
from pp_menushow import MenuShow
from pp_mediashow import MediaShow
