from PyQt5 import QtCore, QtGui
import pyqtgraph as pg
from PyQt5.QtGui import QFileDialog
from PyQt5.QtGui import QSizePolicy
import numpy as np
import peakutils
from scipy.optimize import curve_fit

def getNum(f):
    #key function for sorting files by the number at the end of their filename
    return extract(f.fileName())
    
def extract(text):
    #Strips the number from the end of text and returns it as a float
    for c in range(len(text)):
        if text[c].isdigit() or text[c] == '-':
            return float(text[c:].split('.')[0])
     
def updateText():
    #Updates the contents of the text fields to reflect the positions of the selector regions
    lowBound.setText(str(round(select.getRegion()[0], 4)))
    highBound.setText(str(round(select.getRegion()[1], 4)))
    sLowBound.setText(str(round(secselect.getRegion()[0], 4)))
    sHighBound.setText(str(round(secselect.getRegion()[1], 4)))
    
def updateBounds():
    #Updates the positions of the selector regions on the graph to reflect the contents of the text fields
    select.setRegion([float(lowBound.text()),float(highBound.text())])
    secselect.setRegion([float(sLowBound.text()),float(sHighBound.text())])
    
def fileBrowser():
    #Opens file browser to import data
    directory = QFileDialog.getExistingDirectory(parent=None, caption="Choose Data Directory")
    dirDisp.setText(directory)
    importData()

def importData():
    #Imports data files from the selected folder
    if dirDisp.text() != "":
        #Initialize window elements
        current = QtCore.QDir(dirDisp.text())
        fileinfo = current.entryInfoList(sort=QtCore.QDir.Name)
        checks.clear()
        data.clear()
        temps.clear()
        colors.clear()
        while listLayout.count():
            child = listLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        #Prune list of files
        f = 0
        files = []
        while f < len(fileinfo):
            name = fileinfo[f].fileName()
            if len(name) < 4:
                fileinfo.pop(f)
            elif name[-4:] != ".csv" and name[-4:] != ".txt" and name[-3:] != ".xy":
                fileinfo.pop(f)     
            f = f+1
        
        ##WORKAROUND (to remove nonsensical '..' files)
        fileinfo = fileinfo[1:]
        
        #sort files by terminal number
        fileinfo.sort(key=getNum)
        files = [f.fileName() for f in fileinfo]
         
        #Set up graph color spectrum
        x = np.linspace(1,3,len(files))
        red = np.interp(x, [1,2,3], [0,128,255])
        green = np.interp(x, [1,2,3], [128,90,128])
        blue = np.interp(x, [1,2,3], [255,255,0])
        
        for q in range(len(files)):
            
            colors.append((red[q], green[q], blue[q]))
            
            #Set up checklist
            checks.append(QtGui.QCheckBox(files[q]))
            checks[q].setChecked(True)
            
            p = QtGui.QPalette()
            p.setColor(checks[q].backgroundRole(),QtGui.QColor(*colors[q]))
            checks[q].setPalette(p)
            checks[q].setAutoFillBackground(True)
            
            listLayout.addWidget(checks[q])
            checks[q].show()
            checks[q].stateChanged.connect(checkHandler)
            temps.append(extract(files[q]))
            
            #Import files
            with open(fileinfo[q].absoluteFilePath()) as tempFile:
                raw = tempFile.read()
                rawlist = raw.split('\n')
                x = []
                y = []
                for m in range(len(rawlist)):                
                    
                    if rawlist[m].count(',') > 0:
                        line = rawlist[m].split(',')
                    elif len(rawlist[m]) > 1:
                        line = rawlist[m].split()

                    x.append(float(line[0]))
                    y.append(float(line[1]))
                #Subtract baseline
                y = np.asarray(np.subtract(y, peakutils.baseline(np.asarray(y))))

                data.append(x)
                data.append(y)
        
        #Normalize data
        datmax = np.asarray(data[1::2]).max()
        for i in range(len(data)):
            if i%2:
                data[i] = data[i]/datmax
        
        updatePlots()
        resetBounds()
        updateFits()
    
def resetBounds():
    #Sets the selector regions to default positions
    view = spectraPlots.getPlotItem().getViewBox().viewRange()[0]
    select.setRegion([view[1]*.25, view[1]*.45])
    secselect.setRegion([view[1]*.55, view[1]*.75])

def updatePlots():
    #Clears graph tabs and updates checklist data
    #always called with updateFits
    plotted.clear()
    spectraPlots.clear()
    spectraPlots.getPlotItem().addItem(select)
    spectraPlots.getPlotItem().addItem(secselect)
    sigmaPlots.clear()
    FWHMPlots.clear()
    areaPlots.clear()
    rsqrdPlots.clear()
    ratioPlots.clear()
    for c in range(len(checks)):
        if checks[c].isChecked():
            spectraPlots.plot(data[2*c], data[2*c+1],pen=pg.mkPen(colors[c]))
            plotted.append(c)

def checkHandler():
    #Called when checkboxes are altered
    updatePlots()
    updateFits()

def updateFits():
    #Updates graph tab contents
    #always called with updatePlots
    stdev.clear()
    fwhm.clear()
    area.clear()
    sstdev.clear()
    sfwhm.clear()
    sarea.clear()
    rsqrd.clear()
    srsqrd.clear()
    ratios.clear()
    pltemps.clear()
    #Step through list of checked data sets and trim out the selected regions
    for p in range(len(plotted)):
        indexes = [0,0,0,0]
        for x in data[2*plotted[p]]:
            if (x >= select.getRegion()[0]) and (indexes[0] == 0):
                indexes[0] = data[2*plotted[p]].index(x)
            elif (x >= secselect.getRegion()[0]) and (indexes[2] == 0):
                indexes[2] = data[2*plotted[p]].index(x)  
            elif (x > select.getRegion()[1]) and (indexes[1] == 0):
                indexes[1] = data[2*plotted[p]].index(x) - 1
            elif (x > secselect.getRegion()[1]) and (indexes[3] == 0):
                indexes[3] = data[2*plotted[p]].index(x) - 1   
            
        xdat = np.asarray(data[2*plotted[p]][indexes[0]:indexes[1]])
        ydat = np.asarray(data[2*plotted[p]+1][indexes[0]:indexes[1]])
        sxdat = np.asarray(data[2*plotted[p]][indexes[2]:indexes[3]])
        sydat = np.asarray(data[2*plotted[p]+1][indexes[2]:indexes[3]])
            
        #perform peak fitting and refinement
        params = peakutils.peak.gaussian_fit(xdat, ydat, center_only=False)
        refined, povc = curve_fit(peakutils.peak.gaussian,xdat,ydat, params)
        sparams = peakutils.peak.gaussian_fit(sxdat, sydat, center_only=False)
        srefined, spovc = curve_fit(peakutils.peak.gaussian,sxdat,sydat, sparams)
        
        gaussy = [peakutils.peak.gaussian(x, *refined) for x in xdat]
        sgaussy = [peakutils.peak.gaussian(sx, *srefined) for sx in sxdat]
        
        ssres = np.asarray([(ydat[i]-gaussy[i])**2 for i in range(len(ydat))]).sum()
        ym = ydat.mean()
        sstot = np.asarray([(ydat[i]-ym)**2 for i in range(len(ydat))]).sum()
        rsqrd.append(1 - ssres/sstot)
        ssres = np.asarray([(sydat[i]-sgaussy[i])**2 for i in range(len(sydat))]).sum()
        ym = sydat.mean()
        sstot = np.asarray([(sydat[i]-ym)**2 for i in range(len(sydat))]).sum()
        srsqrd.append(1 - ssres/sstot)
        
        if showGauss.isChecked(): 
            spectraPlots.plot(xdat, gaussy)
            spectraPlots.plot(sxdat, sgaussy)
        
        pltemps.append(temps[plotted[p]])
        stdev.append(refined[2])
        fwhm.append(2*np.sqrt(2*np.log(2))*abs(refined[2]))
        area.append(refined[0]*abs(refined[2])*np.sqrt(2*np.pi))
        ratios.append(np.asarray(gaussy).max()/np.asarray(sgaussy).max())
        sstdev.append(abs(srefined[2]))
        sfwhm.append(2*np.sqrt(2*np.log(2))*abs(srefined[2]))
        sarea.append(srefined[0]*abs(srefined[2])*np.sqrt(2*np.pi))
        
    brushes = [pg.mkBrush(colors[c]) for c in plotted]
    pen1 = pg.mkPen('b',width=2)
    pen2 = pg.mkPen('g',width=2)
        
    sigmaPlots.plot(pltemps,stdev,pen=pen1,symbol='o',symbolBrush=brushes)
    FWHMPlots.plot(pltemps,fwhm,pen=pen1,symbol='o',symbolBrush=brushes)
    areaPlots.plot(pltemps,area,pen=pen1,symbol='o',symbolBrush=brushes)
    rsqrdPlots.plot(pltemps,rsqrd,pen=pen1,symbol='o',symbolBrush=brushes)
    ratioPlots.plot(pltemps,ratios,symbol='o',symbolBrush=brushes)
    sigmaPlots.plot(pltemps,sstdev,pen=pen2,symbol='s',symbolBrush=brushes)
    FWHMPlots.plot(pltemps,sfwhm,pen=pen2,symbol='s',symbolBrush=brushes)
    areaPlots.plot(pltemps,sarea,pen=pen2,symbol='s',symbolBrush=brushes)
    rsqrdPlots.plot(pltemps,srsqrd,pen=pen2,symbol='s',symbolBrush=brushes)

def export():
    #write to a text file
    savename = QFileDialog.getSaveFileName(caption="Export To...",filter="Text files (*.txt)")
    with open(savename[0], "w") as f:
        f.write("Temperatures,xMin1,xMax1,StdDev1,FWHM1,Area1,Rsqr1,xMin2,xMax2,StdDev2,FWHM2,Area2,Rsqr2,Ratios\n")
        for q in range(len(pltemps)):
            f.write(str(pltemps[q])+","+lowBound.text()+","+highBound.text()+","+str(stdev[q])+","+str(fwhm[q])+","+str(area[q])+","+str(rsqrd[q])+",")
            f.write(sLowBound.text()+","+sHighBound.text()+","+str(sstdev[q])+","+str(sfwhm[q])+","+str(sarea[q])+","+str(srsqrd[q])+","+str(ratios[q])+"\n")
    
## Always start by initializing Qt (only once per application)
app = QtGui.QApplication([])

## Define a top-level widget to hold everything
w = QtGui.QWidget()

## Set up the left-hand checklist and text boxes
left = QtGui.QScrollArea()
checkList = QtGui.QWidget()
listLayout = QtGui.QVBoxLayout()
checkList.setLayout(listLayout)
left.setWidget(checkList)
left.setWidgetResizable(True)
checks = []
showGauss = QtGui.QCheckBox('Show Fits')
showGauss.stateChanged.connect(checkHandler)

lowText = QtGui.QLabel("Min")
highText = QtGui.QLabel("Max")
lowBound = QtGui.QLineEdit()
highBound = QtGui.QLineEdit()
sLowBound = QtGui.QLineEdit()
sHighBound = QtGui.QLineEdit()

## Set up menu bar
dirDisp = QtGui.QLineEdit()
mBar = QtGui.QMenuBar()
fileMenu = QtGui.QMenu("Menu")
mBar.addMenu(fileMenu)
dirAction = fileMenu.addAction("Change Directory", fileBrowser)
expAction = fileMenu.addAction("Export", export)

## Set up Tabs
tabs = QtGui.QTabWidget()
spectraTab = QtGui.QWidget()
sigmaTab = QtGui.QWidget()
FWHMTab = QtGui.QWidget()
areaTab = QtGui.QWidget()
rsqrdTab = QtGui.QWidget()
ratioTab = QtGui.QWidget()
tabs.addTab(spectraTab, 'Spectra')
tabs.addTab(sigmaTab, 'Std Dev.')
tabs.addTab(FWHMTab, 'FWHM')
tabs.addTab(areaTab, 'Area')
tabs.addTab(rsqrdTab,'R-Squared')
tabs.addTab(ratioTab,'Peak Ratio')
fitButton = QtGui.QPushButton("Update Fits")
fitButton.clicked.connect(checkHandler)

## Set up the Spectra Tab
spectraLayout = QtGui.QHBoxLayout()
spectraTab.setLayout(spectraLayout)
spectraPlots = pg.PlotWidget()
spectraLayout.addWidget(spectraPlots)
select = pg.LinearRegionItem()
secselect = pg.LinearRegionItem(brush=pg.mkBrush(0,255,0,50))
plotted = []
data = []
temps = []
stdev = []
sstdev = []
fwhm = []
sfwhm = []
area = []
sarea = []
rsqrd = []
srsqrd = []
ratios = []
pltemps = []
colors = []
spectraPlots.getPlotItem().addItem(select)
spectraPlots.getPlotItem().addItem(secselect)

## Set up sigma tab
sigmaLayout = QtGui.QHBoxLayout()
sigmaTab.setLayout(sigmaLayout)
sigmaPlots = pg.PlotWidget()
sigmaLayout.addWidget(sigmaPlots)

## Set up FWHM tab
FWHMLayout = QtGui.QHBoxLayout()
FWHMTab.setLayout(FWHMLayout)
FWHMPlots = pg.PlotWidget()
FWHMLayout.addWidget(FWHMPlots)

## Set up Area tab
areaLayout = QtGui.QHBoxLayout()
areaTab.setLayout(areaLayout)
areaPlots = pg.PlotWidget()
areaLayout.addWidget(areaPlots)

## Set up R-squared tab
rsqrdLayout = QtGui.QHBoxLayout()
rsqrdTab.setLayout(rsqrdLayout)
rsqrdPlots = pg.PlotWidget()
rsqrdLayout.addWidget(rsqrdPlots)

## Set up Peak Ratios tab
ratioLayout = QtGui.QHBoxLayout()
ratioTab.setLayout(ratioLayout)
ratioPlots = pg.PlotWidget()
ratioLayout.addWidget(ratioPlots)

## link up graphs and text boxes
updateText()
select.sigRegionChanged.connect(updateText)
secselect.sigRegionChanged.connect(updateText)
lowBound.editingFinished.connect(updateBounds)
highBound.editingFinished.connect(updateBounds)
sLowBound.editingFinished.connect(updateBounds)
sHighBound.editingFinished.connect(updateBounds)
dirDisp.editingFinished.connect(importData)

## Add widgets to the main window
layout = QtGui.QGridLayout()
w.setLayout(layout)
layout.addWidget(mBar, 0, 0, 1, 2)
layout.addWidget(dirDisp, 0, 3)
layout.addWidget(fitButton, 1, 0)
layout.addWidget(showGauss, 1, 1)
layout.addWidget(lowText, 2, 0)
layout.addWidget(lowBound, 2, 1)
layout.addWidget(sLowBound, 2, 2)
layout.addWidget(highText, 3, 0)
layout.addWidget(highBound, 3, 1)
layout.addWidget(sHighBound, 3, 2)
layout.addWidget(left, 4, 0, 1, 3)  # list widget goes on the left
layout.addWidget(tabs, 1, 3, 4, 1)  # tab box goes on the right

tabs.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
left.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
lowBound.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
highBound.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
sLowBound.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
sHighBound.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

## Display the widget as a new window
w.show()

## Start the Qt event loop
app.exec_()

