export interface CampusCollege {
  id: string
  name: string
  hostels: string[]
}

export interface CampusUniversity {
  id: string
  name: string
  shortName: string
  colleges: CampusCollege[]
}

export const CAMPUS_DIRECTORY: CampusUniversity[] = [
  {
    id: 'ait',
    name: 'Apex Institute of Technology',
    shortName: 'AIT',
    colleges: [
      {
        id: 'ait-eng',
        name: 'School of Engineering & Technology',
        hostels: [
          'Block B • Aryabhatta Hall',
          'Block A • Ramanujan Hall',
          'Block C • Bhaskara Hall'
        ]
      },
      {
        id: 'ait-cs',
        name: 'School of Computing & Artificial Intelligence',
        hostels: [
          'Block B • Aryabhatta Hall',
          'Block D • Visvesvaraya Hall'
        ]
      },
      {
        id: 'ait-mgmt',
        name: 'School of Management Studies',
        hostels: [
          'Block E • Chanakya Hall',
          'Gargi Hall of Residence'
        ]
      }
    ]
  },
  {
    id: 'nit',
    name: 'National Institute of Technology',
    shortName: 'NIT',
    colleges: [
      {
        id: 'nit-eng',
        name: 'Faculty of Engineering & Technology',
        hostels: [
          'Mega Hostel Block 1',
          'Mega Hostel Block 2',
          'Sarabhai Hall of Residence'
        ]
      },
      {
        id: 'nit-sci',
        name: 'School of Applied Sciences',
        hostels: [
          'Kalam Hall of Residence',
          'Kalpana Chawla Bhavan'
        ]
      }
    ]
  },
  {
    id: 'iit',
    name: 'Indian Institute of Technology',
    shortName: 'IIT',
    colleges: [
      {
        id: 'iit-ug',
        name: 'Undergraduate Academic Division',
        hostels: [
          'Nilgiri Hostel',
          'Karakoram Hostel',
          'Aravali Hostel',
          'Kailash Hostel',
          'Jwalamukhi Hostel'
        ]
      },
      {
        id: 'iit-pg',
        name: 'Postgraduate & Research Institute',
        hostels: [
          'Himadri Hall',
          'Satpura Hostel'
        ]
      }
    ]
  },
  {
    id: 'du',
    name: 'Delhi University',
    shortName: 'DU',
    colleges: [
      {
        id: 'du-north',
        name: 'North Campus Academic Enclave',
        hostels: [
          'Jubilee Hall',
          'Mansarovar Hostel',
          'Gwyer Hall',
          'Geetanjali Hostel'
        ]
      },
      {
        id: 'du-south',
        name: 'South Campus Academic Cluster',
        hostels: [
          'Aravali Boys Hostel',
          'Geetanjali Girls Hostel'
        ]
      }
    ]
  },
  {
    id: 'other',
    name: 'Other / Independent Institution',
    shortName: 'Other',
    colleges: [
      {
        id: 'other-general',
        name: 'Campus Academic Unit',
        hostels: [
          'Block B • Aryabhatta Hall',
          'North Wing Residence Hall',
          'South Wing Residence Hall',
          'Main Student Hostel'
        ]
      }
    ]
  }
]

export const DEFAULT_CAMPUS = {
  university: 'Apex Institute of Technology',
  college: 'School of Engineering & Technology',
  hostel: 'Block B • Aryabhatta Hall'
}

export function getCollegesForUniversity(uniName: string): CampusCollege[] {
  const uni = CAMPUS_DIRECTORY.find(u => u.name === uniName)
  return uni ? uni.colleges : (CAMPUS_DIRECTORY[0]?.colleges || [])
}

export function getHostelsForCollege(uniName: string, collegeName: string): string[] {
  const uni = CAMPUS_DIRECTORY.find(u => u.name === uniName)
  if (!uni) return CAMPUS_DIRECTORY[0]?.colleges[0]?.hostels || []
  const col = uni.colleges.find(c => c.name === collegeName)
  return col ? col.hostels : (uni.colleges[0]?.hostels || [])
}
