import type {Donor} from '../../lib/donors.ts';
import {json} from '../../lib/cms.ts';import {identity,ownDonor,publicDonor} from '../../lib/donors.ts';
export async function GET(request:Request){if(!identity(request))return json({error:'Sign in to view your profile'},401);try{const donor=await ownDonor(request);return json({donor:donor?publicDonor(donor):null})}catch(e){console.error(e);return json({error:'Unable to load profile'},503)}}
