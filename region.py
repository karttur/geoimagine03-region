'''
Created on 3 Mar 2021

@author: thomasgumbricht
'''


# Standard library imports

import os

from sys import exit

# Third party imports

# Package application imports

from geoimagine.params import Composition, VectorLayer

import geoimagine.gis as ktgis

from geoimagine.support.modis import ConvertHVstring

from geoimagine.support.easegrid import ConvertXYstring

class IntersectRegions():
    '''
    '''
    
    def _GetModisTilesDict(self):
        '''
        '''
        paramL = ['htile','vtile']
        
        mask = self.pp.process.parameters.defregmask
        
        regtype = 'regionid'
        
        schema = 'modis'
        
        tiles = self.session._SelectRegionTiles(regtype, schema, mask, paramL)

        if len(tiles) == 0:
            
            exitstr = 'Process LinkDefaultRegionsToMODIS can not find any tile region to use for restriction.\n Parameter withintiles: %s' %(self.process.params.mask)
            
            exit(exitstr)
            
        # Craete a list of all tiles "within" the mask
        self.rTiles = [ConvertHVstring(item)['prstr'] for item in tiles]

        # Select all modis tile coordinates
        paramL = ['hvtile','htile','vtile','ullat','ullon','lrlat','lrlon','urlat','urlon','lllat','lllon']
        
        tilecoords = self.session._SelectTileCoords(schema, paramL)
        
        # Create an empty dictionary
        self.modisTileD ={}
        
        # Loop over all tiles
        for tile in tilecoords:
        
            hvtile,htile,vtile,ullat,ullon,lrlat,lrlon,urlat,urlon,lllat,lllon = tile
            
            # if this tile is in the list of withintiles
            if hvtile in self.rTiles:

                # Set the corner geographic coordinates
                llptL = ((ullon,ullat),(urlon,urlat),(lrlon,lrlat),(lllon,lllat))
            
                # Convert the corners to a a geometry
                modtilegeom = ktgis.Geometry()
                
                modtilegeom.PointsToPolygonGeom(llptL)
                
                west, south, east, north = modtilegeom.shapelyGeom.bounds
                
                # Add the edges to the dict - allows a quick and dirty check 
                self.modisTileD[hvtile] = {'hvtile':hvtile,'h':htile,'v':vtile,'geom':modtilegeom,
                                      'west':west,'south':south,'east':east,'north':north}
                
                
    def _GetEaseTilesDict(self,schema):
        '''
        '''
        paramL = ['xtile','ytile']
        
        mask = self.pp.process.parameters.defregmask
        
        regtype = 'regionid'
             
        tiles = self.session._SelectRegionTiles(regtype, schema, mask, paramL)

        if len(tiles) == 0:
            
            exitstr = 'Process LinkDefaultRegionsToEASE can not find any tile region to use for restriction.\n Parameter withintiles: %s' %(self.process.params.mask)
            
            exit(exitstr)
            
        # Create a list of all tiles "within" the mask
        self.rTiles = [ConvertXYstring(item)['prstr'] for item in tiles]

        # Select all tile coordinates
        paramL = ['xytile','xtile','ytile','minxease','maxyease','maxxease','minyease']
        
        tilecoords = self.session._SelectTileCoords(schema, paramL)
        
        # Create an empty dictionary
        self.linkTileD ={}
        
        # Loop over all tiles
        for tile in tilecoords:
        
            xytile,xtile,ytile,minx,maxy,maxx,miny = tile
            
            # if this tile is in the list of withintiles
            if xytile in self.rTiles:

                # Set the corner geographic coordinates
                ptL = ((minx,maxy),(maxx,maxy),(maxx,miny),(minx,miny))
            
                # Convert the corners to a a geometry
                tilegeom = ktgis.Geometry()
                
                tilegeom.PointsToPolygonGeom(ptL)
                
                west, south, east, north = tilegeom.shapelyGeom.bounds
                
                # Add the edges to the dict - allows a quick and dirty check 
                self.linkTileD[xytile] = {'xytile':xytile,'h':xtile,'v':ytile,'geom':tilegeom,
                                      'west':west,'south':south,'east':east,'north':north}
                
    def _GetRegionLayer(self, rec):
        '''
        '''
             
        regioncat, regionid, compid, source, product, content, layerid, prefix, suffix, acqdatestr = rec
        
        # globe is the top region used for defining all other regions
        if regionid == 'globe':
            
            return None
                
        compD = {'source':source, 'product':product, 'content':content, 'layerid':layerid, 'prefix':prefix, 'suffix':suffix}
                        
        system = 'system'
        
        comp = Composition(compD, self.pp.process.parameters, system, self.pp.procsys.srcdivision, self.pp.srcPath)
  
        datumD = {'acqdatestr': acqdatestr, 'acqdate':False}

        locusD = {'locus':regionid, 'locusPath':regionid, 'path':regionid}
        
        # Create and return the layer
        return VectorLayer(comp, locusD, datumD)
        
    def _IdentifyOverlap(self,system, layer,regionid, epsg):
        #Get the layer and the geom

        srcDS,srcLayer = ktgis.ESRIOpenGetLayer(layer.FPN)
        
        for feature in srcLayer.layer: 
                     
            geom = ktgis.Geometry()
            
            #add the feature and extract the geom
            geom.GeomFromFeature(feature)
            
            if srcLayer.geomtype.lower() != 'polygon':
                
                exit('must be a polygon geom for linking')
                
            west, south, east, north = geom.shapelyGeom.bounds
            
            #Get the tiles inside this region
            
            #system ='modis'
            if system == 'modis':
                
                paramL = ['hvtile','htile','vtile','west','south','east','north','ullon','ullat','urlon','urlat','lrlon','lrlat','lllon','lllat']
            
            elif system[0:4] == 'ease':
                
                paramL = ['xytile','xtile','ytile','west','south','east','north','ullon','ullat','urlon','urlat','lrlon','lrlat','lllon','lllat']


            tiles = self.session._SelectTilesWithinWSEN(system, paramL, west, south, east, north)
            
            for tile in tiles:
                
                tileid,path,row,west,south,east,north,ullon,ullat,urlon,urlat,lrlon,lrlat,lllon,lllat = tile
                
                if tileid in self.rTiles:
                    
                    if epsg == 4326:
                    
                        ptL = ((ullon,ullat),(urlon,urlat),(lrlon,lrlat),(lllon,lllat))
                        
                    else:
                        
                        ptL = ((west,north),(east,north),(east,south),(west,south))
                    
                    tilegeom = ktgis.Geometry()
                    
                    tilegeom.PointsToPolygonGeom(ptL)
                    
                    #Get the overlap
                    overlapGeom = tilegeom.ShapelyIntersection(self.linkTileD[tileid]['geom'])  
                    
                    productoverlap = overlapGeom.area/tilegeom.shapelyGeom.area
                    
                    if self.regiontype == 'default': 
                        
                        if system == 'modis':
                            
                            query = {'system':system, 'table':'regions', 'regionid':regionid,'regiontype':self.regiontype, 'overwrite':False, 'delete':False, 'hvtile':tileid,'htile':path, 'vtile':row}
                        
                        elif system[0:4] == 'ease':
                            
                            query = {'system':system, 'table':'regions', 'regionid':regionid,'regiontype':self.regiontype, 'overwrite':False, 'delete':False, 'xytile':tileid,'xtile':path, 'ytile':row}
                        
                            
                    elif self.regiontype == 'tract': 
                          
                        if system == 'modis':
                            
                            query = {'system':system, 'table':'tracts', 'regionid':regionid,'regiontype':self.regiontype, 'overwrite':False, 'delete':False, 'hvtile':tileid,'htile':path, 'vtile':row}
                    
                        elif system[0:4] == 'ease':
                            
                            query = {'system':system, 'table':'tracts', 'regionid':regionid,'regiontype':self.regiontype, 'overwrite':False, 'delete':False, 'xytile':tileid,'xtile':path, 'ytile':row}

                    else:
                        
                        exit (self.regiontype)

                    
                    if productoverlap >= 0:
                        
                        #self.session._InsertModisRegionTile(query)
                        
                        self.session._InsertRegionTile(query)
                        
                        
    def _LinkDefaultRegionTiles(self):
        ''' Link default regions to tiles
        '''
        
        system = self.pp.procsys.dstsystem
        
        epsg = self.pp.procsys.dstepsg
        
        # Set regiontype to default
        self.regiontype = 'default'
        
        # Get the extent of all tiles as a dict
        if system == 'modis':
            
            self._GetModisTilesDict()
            
        elif system == 'ease2n':
        
            self._GetEaseTilesDict(system)
            
        elif system == 'ease2s':
        
            self._GetEaseTilesDict(system)
            
        elif system == 'ease2t':
        
            self._GetEaseTilesDict(system)
        
        # Select all default regions that are not already linked to EASE tiles
        wherestatement = "S.epsg = %(epsg)d AND M.regionid IS NULL" %{'epsg':epsg}
        
        defregs = self.session._SelectDefaultRegionLayers(system, wherestatement)
        
        if self.verbose > 1:
            
            infostr = '        Finding %s tiles linking to %s default regions' %(system, len(defregs))
            
            print (infostr)
            
        # Loop over all selected default regions
        for reg in defregs:
                        
            regionLayer = self._GetRegionLayer(reg)
            
            if regionLayer == None:
                
                continue
                
            if os.path.exists(regionLayer.FPN):
                
                if self.verbose > 1:
                    
                    infostr = '            linking region %s' %(reg[1])
            
                    print (infostr)
                
                regionid = reg[1]
                
                self._IdentifyOverlap(system, regionLayer, regionid, epsg)
                                
            else:
                
                if self.verbose > 1:
                    
                    infostr = '            Layer file %s not available' %(regionLayer.FPN)
            
                    print (infostr)
                        
class ProcessRegion(IntersectRegions):
    '''class for SMAP specific processing
    '''   
        
    def __init__(self, pp, session):
        ''' Processes for managing and translating regions
        '''
            
        # Initiate IntersectRegions
        IntersectRegions.__init__(self)
            
        self.session = session
                
        self.pp = pp  
        
        self.verbose = self.pp.process.verbose 
        
        self.session._SetVerbosity(self.verbose)
        
        print ('        ProcessRegion',self.pp.process.processid) 

        # Direct to sub-processes
        
        if self.pp.process.processid.lower() == 'linkdefaultregiontiles':
                        
            self._LinkDefaultRegionTiles()
 
        else:
            
            exitstr = 'Exiting, processid %(p)s missing in ProcessRegion' %{'p':self.pp.process.processid}
            
            exit(exitstr)
                 
    
                    