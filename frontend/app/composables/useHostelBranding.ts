import { ref, watch, onMounted } from 'vue'

const institutionName = ref('Apex Institute of Technology')
const institutionShort = ref('AIT')
const institutionLogo = ref('') // Optional custom image URL or base64
const hostelName = ref('Block B • Aryabhatta Hall')
const hostelLogo = ref('') // Optional custom hostel logo URL or base64
const hubLocation = ref('2nd Floor Laundry Hub')

let initialized = false

export const useHostelBranding = () => {
  if (import.meta.client && !initialized) {
    initialized = true
    try {
      const savedInst = localStorage.getItem('wq_institution_name')
      if (savedInst) institutionName.value = savedInst

      const savedInstLogo = localStorage.getItem('wq_institution_logo')
      if (savedInstLogo) institutionLogo.value = savedInstLogo

      const savedHostel = localStorage.getItem('wq_hostel_name')
      if (savedHostel) hostelName.value = savedHostel

      const savedHostelLogo = localStorage.getItem('wq_hostel_logo')
      if (savedHostelLogo) hostelLogo.value = savedHostelLogo

      const savedHub = localStorage.getItem('wq_hub_location')
      if (savedHub) hubLocation.value = savedHub
    } catch (e) {
      // Ignore storage errors
    }

    watch(institutionName, (val) => {
      try {
        localStorage.setItem('wq_institution_name', val)
      } catch (e) {}
    })

    watch(institutionLogo, (val) => {
      try {
        localStorage.setItem('wq_institution_logo', val)
      } catch (e) {}
    })

    watch(hostelName, (val) => {
      try {
        localStorage.setItem('wq_hostel_name', val)
      } catch (e) {}
    })

    watch(hostelLogo, (val) => {
      try {
        localStorage.setItem('wq_hostel_logo', val)
      } catch (e) {}
    })

    watch(hubLocation, (val) => {
      try {
        localStorage.setItem('wq_hub_location', val)
      } catch (e) {}
    })
  }

  const setBranding = (
    inst?: string,
    hostel?: string,
    instLogo?: string,
    hLogo?: string,
    hub?: string
  ) => {
    if (inst) institutionName.value = inst
    if (hostel) hostelName.value = hostel
    if (instLogo !== undefined) institutionLogo.value = instLogo
    if (hLogo !== undefined) hostelLogo.value = hLogo
    if (hub) hubLocation.value = hub
  }

  const resetDefaults = () => {
    institutionName.value = 'Apex Institute of Technology'
    institutionShort.value = 'AIT'
    institutionLogo.value = ''
    hostelName.value = 'Block B • Aryabhatta Hall'
    hostelLogo.value = ''
    hubLocation.value = '2nd Floor Laundry Hub'
  }

  return {
    institutionName,
    institutionShort,
    institutionLogo,
    hostelName,
    hostelLogo,
    hubLocation,
    setBranding,
    resetDefaults
  }
}
