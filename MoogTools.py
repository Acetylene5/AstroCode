import scipy
import scipy.interpolate
import numpy
import os


class periodicTable( object ):
    def __init__(self):
        self.Zsymbol_table = {}
        df = open('/home/deen/Code/Python/AstroCode/MOOGConstants.dat', 'r')
        for line in df.readlines():
            l = line.split('-')
            self.Zsymbol_table[int(l[0])] = l[1].strip()
            self.Zsymbol_table[l[1].strip()] = int(l[0])
        df.close()

    def translate(self, ID):
        retval = self.Zsymbol_table[ID]
        return retval

class VALD_Line( object ):
    def __init__(self, line1, line2, pt):
        l1 = line1.split(',')
        l2 = line2.split()
        self.element = pt.translate(l1[0].strip('\'').split()[0])
        self.ionization = int(l1[0].strip('\'').split()[1])-1
        self.species = self.element + self.ionization/10.0
        self.wl = float(l1[1])
        self.loggf = float(l1[2])
        self.expot_lo = float(l1[3])
        self.J_lo = float(l1[4])
        self.expot_hi = float(l1[5])
        self.J_hi = float(l1[6])
        self.g_lo = float(l1[7])
        self.g_hi = float(l1[8])
        self.g_eff = float(l1[9])
        self.radiative = float(l1[10])
        self.stark = float(l1[11])
        self.VdW = float(l1[12])
        self.DissE = -99.0
        self.transition = line2.strip().strip('\'')

        if (self.g_lo == 99.0):
            if not (self.species in [70.1, 25.2]):
                angmom = {"S":0, "P":1, "D":2, "F":3, "G":4, "H":5, "I":6, "K":7, "L":8, "M":9}
                n = 0
                try:
                    for char in self.transition:
                        if char.isdigit():
                            S = (float(char)-1.0)/2.0
                        if ((char.isupper()) & (n < 2)):
                            n+=1
                            L = angmom[char]
                            if n == 1:
                                if (self.J_lo > 0.0):
                                    self.g_lo = 1.5+(S*(S+1.0)-L*(L+1))/(2*self.J_lo*(self.J_lo+1))
                                else:
                                    self.g_lo = 0.0
                            else:
                                if (self.J_hi > 0.0):
                                    self.g_hi = 1.5+(S*(S+1.0)-L*(L+1))/(2*self.J_hi*(self.J_hi+1))
                                else:
                                    self.g_hi = 0.0
                except:
                    self.g_lo = 0.0
                    self.g_hi = 0.0
                    print("Ooops!")
            else:
                self.g_lo = 0.0
                self.g_hi = 0.0
   
        self.lower = Observed_Level(self.J_lo, self.g_lo, self.expot_lo)
        self.upper = Observed_Level(self.J_hi, self.g_hi, self.expot_lo+12400.0/self.wl)
        self.zeeman = {}
        self.zeeman["NOFIELD"] = [self.wl,self.loggf]

    def zeeman_splitting(self, B, **kwargs):
        self.compute_zeeman_transitions(B, **kwargs)
        wl = []
        lgf = []
        for transition in self.pi_transitions:
            if (transition.weight > 0):
                wl.append(transition.wavelength)
                lgf.append(numpy.log10(transition.weight*
                    10.0**(self.loggf)))
        self.zeeman["PI"] = [numpy.array(wl), numpy.array(lgf)]

        wl = []
        lgf = []
        for transition in self.lcp_transitions:
            if (transition.weight > 0):
                wl.append(transition.wavelength)
                lgf.append(numpy.log10(transition.weight*
                    10.0**(self.loggf)))
        self.zeeman["LCP"] = [numpy.array(wl), numpy.array(lgf)]

        wl = []
        lgf = []
        for transition in self.rcp_transitions:
            if (transition.weight > 0):
                wl.append(transition.wavelength)
                lgf.append(numpy.log10(transition.weight*
                    10.0**(self.loggf)))
        self.zeeman["RCP"] = [numpy.array(wl), numpy.array(lgf)]

    def compute_zeeman_transitions(self, B, **kwargs):

        bohr_magneton = 5.78838176e-5        #eV*T^-1
        hc = 12400                           #eV*Angstroms
        lower_energies = {}
        upper_energies = {}
        for mj in self.lower.mj:
            lower_energies[mj]=self.lower.E+mj*self.lower.g*bohr_magneton*B

        for mj in self.upper.mj:
            upper_energies[mj] = self.upper.E+mj*self.upper.g*bohr_magneton*B

        pi_transitions = []
        lcp_transitions = []
        rcp_transitions = []

        pi_weight = 0.0
        lcp_weight = 0.0
        rcp_weight = 0.0

        delta_J = self.upper.J - self.lower.J
        J1 = self.lower.J

        self.geff = (0.5*(self.lower.g+self.upper.g)
                +0.25*(self.lower.g-self.upper.g)*(self.lower.J*(self.lower.J+1)-
                self.upper.J*(self.upper.J+1.0)))

        for mj in lower_energies.keys():
            if (delta_J == 0.0):
                if upper_energies.has_key(mj+1.0):    #delta Mj = +1 sigma component
                    weight = (J1-mj)*(J1+mj+1.0)
                    rcp_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj+1]-lower_energies[mj]), weight,
                        mj+1, mj))
                    rcp_weight+=weight
                if upper_energies.has_key(mj):    #delta Mj = 0 Pi component
                    weight = mj**2.0
                    pi_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj]-lower_energies[mj]), weight,
                        mj, mj))
                    pi_weight+=weight
                if upper_energies.has_key(mj-1.0):    #delta Mj = -1 sigma component
                    weight = (J1+mj)*(J1-mj+1.0)
                    lcp_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj-1]-lower_energies[mj]), weight,
                        mj-1, mj))
                    lcp_weight+=weight
            if (delta_J == 1.0):
                if upper_energies.has_key(mj+1.0):    #delta Mj = +1 sigma component
                    weight = (J1+mj+1.0)*(J1+mj+2.0)
                    rcp_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj+1]-lower_energies[mj]), weight,
                        mj+1, mj))
                    rcp_weight+=weight
                if upper_energies.has_key(mj):    #delta Mj = 0 Pi component
                    weight = (J1+1.0)**2.0 - mj**2.0
                    pi_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj]-lower_energies[mj]), weight,
                        mj, mj))
                    pi_weight+=weight
                if upper_energies.has_key(mj-1.0):    #delta Mj = -1 sigma component
                    weight = (J1-mj+1.0)*(J1-mj+2.0)
                    lcp_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj-1]-lower_energies[mj]), weight,
                        mj-1, mj))
                    lcp_weight+=weight
            if (delta_J == -1.0):
                if upper_energies.has_key(mj+1.0):    #delta Mj = +1 sigma component
                    weight = (J1-mj)*(J1-mj-1.0)
                    rcp_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj+1]-lower_energies[mj]), weight,
                        mj+1, mj))
                    rcp_weight+=weight
                if upper_energies.has_key(mj):    #delta Mj = 0 Pi component
                    weight = J1**2.0 - mj**2.0
                    pi_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj]-lower_energies[mj]), weight,
                        mj, mj))
                    pi_weight+=weight
                if upper_energies.has_key(mj-1.0):    #delta Mj = -1 sigma component
                    weight = (J1+mj)*(J1+mj-1.0)
                    lcp_transitions.append(zeemanTransition(hc/
                        (upper_energies[mj-1]-lower_energies[mj]), weight,
                        mj-1, mj))
                    lcp_weight+=weight

        for transition in rcp_transitions:
            transition.weight /= rcp_weight
        for transition in lcp_transitions:
            transition.weight /= lcp_weight
        for transition in pi_transitions:
            transition.weight /= pi_weight

        self.pi_transitions = pi_transitions
        self.lcp_transitions = lcp_transitions
        self.rcp_transitions = rcp_transitions

    def dump(self, **kwargs):
        if "out" in kwargs:
            out = kwargs["out"]
            if kwargs["mode"].upper() == 'MOOG':
                if( (self.expot_lo < 20.0) & (self.species % 1 <= 0.2)):
                    if (self.DissE == -99.0):
                        for i in range(len(self.zeeman["PI"][0])):
                            out.write('%10.3f%10s%10.3f%10.5f' %
                               (self.zeeman["PI"][0][i],
                               self.species,self.expot_lo,self.zeeman["PI"][1][i]))
                            if self.VdW == 0:
                                out.write('%20s%20.3f'% (' ',0.0))
                            else:
                                out.write('%10.3f%20s%10.3f' %
                                        (self.VdW, ' ', 0.0))
                            if self.radiative == 0:
                                out.write('%10.3s'% (' '))
                            else:
                                out.write('%10.3f' %
                                        (self.radiative))
                            if self.stark == 0:
                                out.write('%10s\n'% (' '))
                            else:
                                out.write('%10.3f\n' %
                                        (self.stark))
                        for i in range(len(self.zeeman["LCP"][0])):
                            out.write('%10.3f%10s%10.3f%10.5f' %
                               (self.zeeman["LCP"][0][i],
                               self.species,self.expot_lo,self.zeeman["LCP"][1][i]))
                            if self.VdW == 0:
                                out.write('%20s%20.3f'% (' ',-1.0))
                            else:
                                out.write('%10.3f%20s%10.3f' %
                                        (self.VdW, ' ', -1.0))
                            if self.radiative == 0:
                                out.write('%10.3s'% (' '))
                            else:
                                out.write('%10.3f' %
                                        (self.radiative))
                            if self.stark == 0:
                                out.write('%10s\n'% (' '))
                            else:
                                out.write('%10.3f\n' %
                                        (self.stark))
                        for i in range(len(self.zeeman["RCP"][0])):
                            out.write('%10.3f%10s%10.3f%10.5f' %
                               (self.zeeman["RCP"][0][i],
                               self.species,self.expot_lo,self.zeeman["RCP"][1][i]))
                            if self.VdW == 0:
                                out.write('%20s%20.3f'% (' ',1.0))
                            else:
                                out.write('%10.3f%20s%10.3f' %
                                        (self.VdW, ' ', 1.0))
                            if self.radiative == 0:
                                out.write('%10.3s'% (' '))
                            else:
                                out.write('%10.3f' %
                                        (self.radiative))
                            if self.stark == 0:
                                out.write('%10s\n'% (' '))
                            else:
                                out.write('%10.3f\n' %
                                        (self.stark))
                    else:
                        #RCP
                        out.write('%10.3f%10.5f%10.3f%10.3f' %
                                (self.wl, self.species, self.expot_lo,self.loggf))
                        if self.VdW == 0.0:
                            out.write('%10s%10.3f%20.3f' %
                                    (' ',self.DissE, 1.0))
                        else:
                            out.write('%10.3f%10.3f%20.3f' %
                                    (self.VdW, self.DissE, 1.0))
                        if self.radiative == 0:
                            out.write('%10.3s'% (' '))
                        else:
                            out.write('%10.3f' %
                                    (self.radiative))
                        if self.stark == 0:
                            out.write('%10s\n'% (' '))
                        else:
                            out.write('%10.3f\n' %
                                    (self.stark))
                        #PI
                        out.write('%10.3f%10.5f%10.3f%10.3f' %
                                (self.wl, self.species, self.expot_lo,self.loggf))
                        if self.VdW == 0.0:
                            out.write('%10s%10.3f%20.3f' %
                                    (' ',self.DissE, 0.0))
                        else:
                            out.write('%10.3f%10.3f%20.3f' %
                                    (self.VdW, self.DissE, 0.0))
                        if self.radiative == 0:
                            out.write('%10.3s'% (' '))
                        else:
                            out.write('%10.3f' %
                                    (self.radiative))
                        if self.stark == 0:
                            out.write('%10s\n'% (' '))
                        else:
                            out.write('%10.3f\n' %
                                    (self.stark))
                        #LCP
                        out.write('%10.3f%10.5f%10.3f%10.3f' %
                                (self.wl, self.species, self.expot_lo,self.loggf))
                        if self.VdW == 0.0:
                            out.write('%10s%10.3f%20.3f' %
                                    (' ',self.DissE, -1.0))
                        else:
                            out.write('%10.3f%10.3f%20.3f' %
                                    (self.VdW, self.DissE, -1.0))
                        if self.radiative == 0:
                            out.write('%10.3s'% (' '))
                        else:
                            out.write('%10.3f' %
                                    (self.radiative))
                        if self.stark == 0:
                            out.write('%10s\n'% (' '))
                        else:
                            out.write('%10.3f\n' %
                                    (self.stark))
            elif kwargs["mode"].upper() == "MOOGSCALAR":
                if( (self.expot_lo < 20.0) & (self.species % 1 <= 0.2)):
                    if (self.DissE == -99.0):
                        out.write('%10.3f%10s%10.3f%10.5f' %
                           (self.zeeman["NOFIELD"][0],
                           self.species,self.expot_lo,
                           self.zeeman["NOFIELD"][1]))
                        if self.VdW == 0:
                            out.write('%40s'% (' '))
                        else:
                            out.write('%10.3f%30s' %
                                    (self.VdW, ' '))
                        if self.radiative == 0:
                            out.write('%10.3s'% (' '))
                        else:
                            out.write('%10.3f' %
                                    (self.radiative))
                        if self.stark == 0:
                            out.write('%10s\n'% (' '))
                        else:
                            out.write('%10.3f\n' %
                                    (self.stark))

class zeemanTransition( object):
    def __init__(self, wavelength, weight, m_up, m_low):
        self.wavelength = wavelength
        self.weight = weight
        self.m_up = m_up
        self.m_low = m_low

    def __eq__(self, other):
        return ( (self.wavelength == other.wavelength) &
                (self.m_up == other.m_up) & (self.m_low == other.m_low) )

class Observed_Level( object ):
    def __init__(self, J, g, E):
        self.E = E
        self.J = J
        if g != 99:
            self.g = g
        else:
            self.g = 1.0

        self.mj = numpy.arange(self.J, (-1.0*self.J)-0.5, step = -1)

def parse_VALD(VALD_list, strong_file, molecules, wl_start, wl_stop, Bfield):
    pt = periodicTable()

    strong = []
    for line in open(strong_file, 'r'):
        l = line.split()
        strong.append([float(l[0]), float(l[1])])
    
    vald_in = open(VALD_list, 'r')
    l1 = ''
    l2 = ''
    stronglines = []
    weaklines = []
    for line in vald_in:
        if line[0] != '#':
            if line[0] == '\'':
                l1 = line
            else:
                l2 = line
                current_line = VALD_Line(l1, l2, pt)
                wl = current_line.wl
                if ( (wl > wl_start) & (wl < wl_stop) ):
                    current_line.zeeman_splitting(Bfield)
                    species = current_line.species
                    if ( [wl, species] in strong):
                        stronglines.append(current_line)
                    else:
                        weaklines.append(current_line)

    return stronglines, weaklines

def write_par_file(wl_start, wl_stop, stage_dir, b_dir, prefix, temps=None, 
        gravs=None, mode='gridstokes', strongLines=False, **kwargs):
    if mode=='gridstokes':
        fn = 'batch.gridstokes'
        suffix = '.stokes'
    elif mode == 'gridsyn':
        fn = 'batch.gridsyn'
        suffix = '.scalar'
    elif mode == 'stokes':
        fn = 'batch.stokes'
        suffix = '.stokes'
    elif mode == 'synth':
        fn = 'batch.synth'
        suffix = '.scalar'

    outfile_name = os.path.join(stage_dir,'Parfiles', b_dir, fn)

    if "OUT_DIR" in kwargs.keys():
        output_prefix = kwargs["OUT_DIR"]
    else:
        output_prefix = '../../Output/'+b_dir+'/'

    line_prefix = '../../Linelists/'+b_dir+'/'

    labels = {'terminal':'x11',
            'strong':1, 
            'atmosphere':1, 
            'molecules':2,
            'lines':1,
            'damping':1,
            'freeform':0,
            'flux/int':0}
            #'plot':2, 
            #'obspectrum':5}
    file_labels = {'summary_out':'../../Output/'+b_dir+'/summary.out',
            'standard_out':output_prefix+'out1',
            'smoothed_out':output_prefix+'smoothed.out',
            'atmos_dir':'/home/deen/Data/Atmospheres/MARCS/',
            'out_dir':output_prefix,
            'lines_in':line_prefix+prefix+'_weak_linelist'+suffix,
            'stronglines_in':line_prefix+prefix+'_strong_linelist'+suffix}
            #'model_in':'model.md',
            #'observed_in':'observed.dat'}


    for l in labels:
        if l in kwargs:
            labels[l] = kwargs[l]
            
    for fl in file_labels:
        if fl in kwargs:
            file_labels[fl] = kwargs[fl]

    pf = open(outfile_name, 'w')

    pf.write(mode+'\n')
    for fl in file_labels:
        pf.write(fl+'   \''+file_labels[fl]+'\'\n')
    for l in labels:
        pf.write(l+'    '+str(labels[l])+'\n')

    pf.write('synlimits\n')
    pf.write('               '+str(wl_start)+' '
             +str(wl_stop)+' 0.01 3.50\n')
    pf.write('plotpars       1\n')
    pf.write('               '+str(wl_start)+' '
             +str(wl_stop)+' 0.02 1.00\n')
    pf.write('               0.00 0.000 0.000 1.00\n')
    pf.write('               g 0.150 0.00 0.00 0.00 0.00\n')

    if ( (mode=='gridstokes') | (mode=='gridsyn')):
        run_number = 1

        if (not temps):
            temps = range(2500, 4100, 100)+range(4250, 6250, 250)
        if (not gravs):
            gravs = range(300, 550, 50)

        for T in temps:
            for G in gravs:
                pf.write('RUN            '+str(run_number)+'\n')
                if mode == 'gridstokes':
                    pf.write('stokes_out   \''+prefix+
                        '_MARCS_T'+str(T)+'G'+str(G)+'\'\n')
                else:
                    pf.write('smoothed_out   \''+prefix+
                        '_MARCS_T'+str(T)+'G'+str(G)+'\'\n')
                pf.write('hardpost_out   \'../../Output/'+b_dir+'/dummy.ps\'\n')
                pf.write('model_in       \'MARCS_T'+
                        str(T)+'_G'+str(G/100.0)+'_M0.0_t2.0.md\'\n')
                pf.write('abundances     1  1\n')
                pf.write('    12      0.0\n')
                run_number += 1
    pf.close()



class MoogStokes_IV_Spectrum( object ):
    def __init__(self, name, **kwargs):
        self.name = name
        if "DIR" in kwargs.keys():
            self.directory = kwargs["DIR"]
        else:
            self.directory = '../'
        if "DELTAV" in kwargs.keys():
            self.deltav = kwargs["DELTAV"]
        else:
            self.deltav = 0.1            #  wl spacing in km/s
        if "VSINI" in kwargs.keys():
            self.vsini = kwargs["VSINI"]
        else:
            self.vsini = 0.0

        self.angle_file = self.directory+self.name+'.angles'
        self.continuum_file = self.directory+self.name+'.continuum'
        self.I_file = self.directory+self.name+'.spectrum_I'
        self.V_file = self.directory+self.name+'.spectrum_V'

        self.nangles = 0
        self.phi = []
        self.mu = []
        self.wl = []
        self.I = []
        self.V = []
        self.continuum = []

        self.loadAngles()
        self.loadSpectra()
        self.interpolateSpectra()
        self.diskInt()


    def loadAngles(self):
        df = open(self.angle_file, 'r')
        for line in df:
            l = line.split()
            if len(l) == 1:
                self.nangles = int(l[0])
            else:
                self.phi.append(float(l[1]))
                self.mu.append(float(l[2]))

        self.phi = numpy.array(self.phi)
        self.mu = numpy.array(self.mu)

    def loadSpectra(self):
        df_I = open(self.I_file, 'r')
        df_V = open(self.V_file, 'r')
        df_C = open(self.continuum_file, 'r')

        continuum = []
        I = []
        V = []
        wl = []
        for line in df_C:
            l = line.split()
            wl.append(float(l[0]))
            a = []
            for fluxes in l[1:]:
                try:
                    a.append(float(fluxes))
                except:
                    print("Warning! Crazy Continuum format!", fluxes)
                    a.append(float(0.0))
            continuum.append(a)

        for line in df_I:
            l = line.split()
            a = []
            for fluxes in l[1:]:
                try:
                    a.append(float(fluxes))
                except:
                    print("Woah there pardner! Crazy format - Stokes I!", fluxes)
                    a.append(float(0.0))
            I.append(a)

        for line in df_V:
            l = line.split()
            a = []
            for fluxes in l[1:]:
                try:
                    a.append(float(fluxes))
                except:
                    print("Woah there pardner! Crazy format - Stokes V!", fluxes)
                    a.append(float(0.0))
            V.append(a)

        self.wl = numpy.array(wl)
        I = numpy.array(I)
        V = numpy.array(V)
        continuum = numpy.array(continuum)
        self.continuum = continuum.transpose()
        self.I = I.transpose()/self.continuum
        self.V = V.transpose()/self.continuum

        wave = numpy.mean(self.wl)
        if ((1.0/(wave/10000.0)) < 2.4):
            self.alpha = -0.023 + 0.292/(wave/10000.0)
        else:
            self.alpha = -0.507 + 0.441/(wave/10000.0)

    def interpolateSpectra(self):
        deltav = self.deltav
        c = 3e5                        #km/s
        wl_start = numpy.min(self.wl)
        wl_max = numpy.max(self.wl)
        new_wl = []
        new_wl.append(wl_start)
        while new_wl[-1] < wl_max:
            d_lambda = new_wl[-1]*deltav/c
            new_wl.append(new_wl[-1]+d_lambda)
        self.new_wl = numpy.array(new_wl[0:-1])

        new_I = []
        new_V = []
        for I,V in zip(self.I, self.V):
            fI = scipy.interpolate.UnivariateSpline(self.wl, I, s=0)
            fV = scipy.interpolate.UnivariateSpline(self.wl, V, s=0)
            new_I.append(fI(self.new_wl))
            new_V.append(fV(self.new_wl))

        self.new_I = numpy.array(new_I)
        self.new_V = numpy.array(new_V)

    def diskInt(self):
        deltav = self.deltav
        vsini = self.vsini
        c = 3e5
        limb_darkening = []
        for i in range(len(self.mu)):
            limb_darkening.append(1.0-(1.0-self.mu[i]**(self.alpha)))

        self.limb_darkening = numpy.array(limb_darkening)
        continuum = []
        for i in range(len(self.mu)):
            self.new_I[i] *= self.limb_darkening[i]
            continuum.append(numpy.ones(len(self.new_I[i]))
                    *self.limb_darkening[i])

        continuum = numpy.array(continuum)

        self.final_spectrum = rtint(self.mu, self.new_I,
                continuum, deltav, vsini, 0.0)
        

def rtint(mu, inten, cont, deltav, vsini_in, vrt_in, **kwargs):
    """
    This is a python translation of Jeff Valenti's disk integration routine
    
    PURPOSE:
        Produces a flux profile by integrating intensity profiles (sampled
           at various mu angles) over the visible stellar surface.

    Calling Sequence:
        flux = rtint(mu, inten, deltav, vsini, vrt)

    INPUTS:
        MU: list of length nmu cosine of the angle between the outward normal
            and the line of sight for each intensity spectrum INTEN
        INTEN:  list (of length nmu) numpy arrays (each of length npts)
            intensity spectra at specified values of MU
        DELTAV: (scalar) velocity spacing between adjacent spectrum points in
            INTEN (same units as VSINI and VRT)

        VSIN (scalar) maximum radial velocity, due to solid-body rotation
        VRT (scalar) radial-tangential macroturbulence parameter, i.e.. sqrt(2)
            times the standard deviation of a Gaussian distribution of 
            turbulent velocities.  The same distribution function describes
            the raidal motions of one component and the tangential motions of
            a second component.  Each component covers half the stellar surface.
            See "Observation and Analysis of Stellar Photospheres" by Gray.

    INPUT KEYWORDS:
        OSAMP: (scalar) internal oversamping factor for the convolutions.  By
            default, convolutions are done using the input points (OSAMP=1), 
            but when OSAMP is set to higher integer values, the input spectra
            are first oversamping via cubic spline interpolation.

    OUTPUTS:
        function value: numpy array of length npts producing the disk-integrated
            flux profile.

    RESTRICTIONS:
        Intensity profiles are weighted by the fraction of the projected stellar
            surface they represent, apportioning the area between adjacent MU
            points equally.  Additional weights (such as those used in a Gauss-
            Legendre quadrature) cannot meaningfully be used in this scheme.
            About twice as many points are required with this scheme to achieve
            the same precision of Gauss-Legendre quadrature.
        DELTAV, VSINI, and VRT must all be in the same units (e.q. km/s).
        If specified, OSAMP should be a positive integer

    AUTHOR'S REQUEST:
        If you use this algorithm in work that you publish, please cite...

    MODIFICATION HISTORY:
            Feb 88  GM Created ANA version
         13 Oct 92 JAV Adapted from G. Marcy's ANA routine of same name
         03 Nov 93 JAV Switched to annular convolution technique
         12 Nov 93 JAV Fixed bug. Intensity components not added when vsini=0
         14 Jun 94 JAV Reformatted for "public" release.  Heavily commented.
                 Pass deltav instead of 2.998d5/deltav.  Added osamp
                    keyword.  Added rebinning logic and end of routine.
                 Changed default osamp from 3 to 1.
         20 Feb 95 JAV Added mu as an argument to handle arbitrary mu sampling
                    and remove ambiguity in intensity profile ordering.
                 Interpret VTURB as sqrt(2)*sigma instead of just sigma
                 Replaced call_external with call to spl_{init|interp}.
         03 Apr 95 JAV Multiply flux by !pi to give observed flux.
         24 Oct 95 JAV Force "nmk" padding to be at least 3 pixels
         18 Dec 95 JAV Renamed from dkint() to rtint().  No longer make local
                    copy of intensities.  Use radial-tangential instead of 
                    isotropic Gaussian macroturbulence.
         26 Jan 99 JAV For NMU=1 and VSINI=0, assume resolved solar surface;
                    apply R-T macro, but supress vsini broadening.
         01 Apr 99 GMH Use annuli weights, rather than assuming equal area.
         27 Feb 13 CPD Translated to Python

    """
    
    #make local copies of various input variables, which will be altered below
    vsini = float(vsini_in)
    vrt = float(vrt_in)

    if "OSAMP" in kwargs:
        os = max(round(kwargs["OSAMP"]), 1)
    else:
        os = 1

    #Convert input MU to projected radii, R of annuli for a star of unit radius
    #(which is just sine rather than cosine of the angle between the outward
    #normal and the LOS)
    rmu = numpy.sqrt(1.0-mu**2)

    #Sort the projected radii and corresponding intensity spectra into ascending
    #order (i.e. from disk center to the limb), which is equivalent to sorting
    #MU in decending order
    order = numpy.argsort(rmu)
    rmu = rmu[order]
    nmu = len(mu)
    if (nmu == 1):
        vsini = 0.0

    #Calculate the projected radii for boundaries of disk integration annuli.
    #The n+1 boundaries are selected such that r(i+1) exactly bisects the area
    #between rmu(i) and rmu(i+1).  The innermost boundary, r(0) is set to 0
    #(Disk center) and the outermost boundary r(nmu) is set to to 1 (limb).
    if ((nmu > 1) | (vsini != 0)):
        r = numpy.sqrt(0.5*(rmu[0:-1]**2.0+rmu[1:])).tolist()
        r.insert(0, 0.0)
        r.append(1.0)
        r = numpy.array(r)

    #Calculate integration weights for each disk integration annulus.  The
    #weight is just given by the relative area of each annulus, normalized such
    #that the sum of all weights is unity.  Weights for limb darkening are
    #included explicitly in the intensity profiles, so they aren't needed here.
        wt = r[1:]**2.0 - r[0:-1]**2.0
    else:
        wt = numpy.array([1.0])
    
    #Generate index vectors for input and oversampled points.  Note that the
    #oversampled indicies are carefully chosen such that every "os" finely
    #sampled points fit exactly into one input bin.  This makes it simple to
    #"integrate" the finely sampled points at the end of the routine.

    npts = len(inten[0])
    xpix = numpy.arange(npts)
    nfine = os*npts
    xfine = 0.5/os * 2.0*numpy.arange(nfine)-os+1

    #Loop through annuli, constructing and convolving with rotation kernels.
    dummy = 0
    yfine = numpy.zeros(nfine)
    cfine = numpy.zeros(nfine)
    flux = numpy.zeros(nfine)
    continuum = numpy.zeros(nfine)
    for m, y, c, w, i in zip(mu, inten, cont, wt, range(nmu)):
        #use cubic spline routine to make an oversampled version of the
        #intensity profile for the current annulus.
        if os== 1:
            yfine = y.copy()
            cfine = c.copy()
        else:
            yspl = scipy.interpolate.splrep(xpix, y)
            cspl = scipy.interpolate.splref(xpix, c)
            yfine = scipy.interpolate.splev(yspl, xfine)
            cfine = scipy.interpolate.splev(cspl, xfine)

    # Construct the convolution kernel which describes the distribution of 
    # rotational velocities present in the current annulus.  The distribution
    # has been derived analyitically for annuli of arbitrary thickness in a 
    # rigidly rotating star.  The kernel is constructed in two places: one 
    # piece for radial velocities less than the maximum velocity along the
    # inner edge of the annulus, and one piece for velocities greater than this
    # limit.
        if vsini > 0:
            r1 = r[i]
            r2 = r[i+1]
            dv = deltav/os
            maxv = vsini * r2
            nrk = 2*long(maxv/dv) + 3
            v = dv * (numpy.arange(nrk) - ((nrk-1)/2.))
            rkern = numpy.zeros(nrk)
            j1 = scipy.where(abs(v) < vsini*r1)
            if len(j1[0]) > 0:
                rkern[j1] = (numpy.sqrt((vsini*r2)**2 - v[j1]**2)-
                        numpy.sqrt((vsini*r1)**2 - v[j1]**2))
            j2 = scipy.where((abs(v) >= vsini*r1) & (abs(v) <= vsini*r2))
            if len(j2[0]) > 0:
                rkern[j2] = numpy.sqrt((vsini*r2)**2 - v[j2]**2)
            rkern = rkern / rkern.sum()   # normalize kernel


    # Convolve the intensity profile with the rotational velocity kernel for
    # this annulus.  Pad the end of each profile with as many points as are in
    # the convolution kernel.  This reduces Fourier ringing.  The convolution 
    # may also be done with a routine called "externally" which efficiently
    # shifts and adds.
            if nrk > 3:
                yfine = scipy.convolve(yfine, rkern, mode='same')
                cfine = scipy.convolve(cfine, rkern, mode='same')

    # Calculate projected simga for radial and tangential velocity distributions.
        sigma = os*vrt/numpy.sqrt(2.0) /deltav
        sigr = sigma * m
        sigt = sigma * numpy.sqrt(1.0 - m**2.)

    # Figure out how many points to use in macroturbulence kernel
        nmk = max(min(round(sigma*10), (nfine-3)/2), 3)

    # Construct radial macroturbulence kernel w/ sigma of mu*VRT/sqrt(2)
        if sigr > 0:
            xarg = (numpy.range(2*nmk+1)-nmk) / sigr   # exponential arg
            mrkern = numpy.exp(max((-0.5*(xarg**2)),-20.0))
            mrkern = mrkern/mrkern.sum()
        else:
            mrkern = numpy.zeros(2*nmk+1)
            mrkern[nmk] = 1.0    #delta function

    # Construct tangential kernel w/ sigma of sqrt(1-mu**2)*VRT/sqrt(2.)
        if sigt > 0:
            xarg = (numpy.range(2*nmk+1)-nmk) /sigt
            mtkern = exp(max((-0.5*(xarg**2)), -20.0))
            mtkern = mtkern/mtkern.sum()
        else:
            mtkern = numpy.zeros(2*nmk+1)
            mtkern[nmk] = 1.0

    # Sum the radial and tangential components, weighted by surface area
        area_r = 0.5
        area_t = 0.5
        mkern = area_r*mrkern + area_t*mtkern

    # Convolve the total flux profiles, again padding the spectrum on both ends 
    # to protect against Fourier rinnging.
        yfine = scipy.convolve(yfine, mkern, mode='same')
        cfine = scipy.convolve(cfine, mkern, mode='same')

    # Add contribution from current annulus to the running total
        flux += w*yfine
        continuum += w*cfine

    return flux/continuum