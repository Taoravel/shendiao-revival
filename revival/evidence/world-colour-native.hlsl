sampler2D g_renderTex;											
float g_param[8];												
struct PS_INPUT												
{																
   float2 vpos: VPOS;											
	float4 c0: COLOR0;											
	float2 TexCoord: TEXCOORD0;									
};																
struct PS_OUTPUT												
{																
	float4 cr: COLOR;											
};																
PS_OUTPUT main( PS_INPUT input )								
{																
	PS_OUTPUT output = (PS_OUTPUT)0;							
	float4 fResult = tex2D(g_renderTex, input.TexCoord);		
		fResult = fResult*input.c0;								
	float fx = (input.vpos.x - g_param[6])/1.5f;							
	float fy = input.vpos.y - g_param[7];									
	float4 fvalue = float4(0.5f, 1.0f, 1.3333f, 250.0f);					
	float fdis = sqrt(fx*fx + fy*fy)/fvalue.w;								
	float fTemp = 0.25f;													
	if(fdis<fTemp)															
		fdis = fTemp;														
if( fdis < fvalue.y)														
{																			
	g_param[0] = fvalue.z*g_param[0]*(fdis-fTemp);							
	g_param[1] = fvalue.z*g_param[1]*(fdis-fTemp);							
	g_param[2] = fvalue.z*g_param[2]*(fdis-fTemp);							
	g_param[3] = fvalue.z*g_param[3]*(fdis-fTemp);							
	g_param[4] = fvalue.z*(g_param[4]-fvalue.y)*(fdis-fTemp) +fvalue.y;		
	g_param[5] = fvalue.z*g_param[5]*(fdis-fTemp);							
}																			
	float4 fDeltacolor;													
	fDeltacolor.x = (fvalue.y-fResult.x)*g_param[0];					
	fResult.x += fDeltacolor.x;											
	fResult.y -= fDeltacolor.x*fvalue.x;								
	fResult.z -= fDeltacolor.x*fvalue.x;   								
	saturate(fResult.xyz);												
	fDeltacolor.y = (fvalue.y-fResult.y)*g_param[1]; 					
	fResult.y += fDeltacolor.y;											
	fResult.x -= fDeltacolor.y*fvalue.x;								
	fResult.z -= fDeltacolor.y*fvalue.x;   								
	saturate(fResult.xyz);												
	fDeltacolor.z = (fvalue.y-fResult.z)*g_param[2];					
	fResult.z += fDeltacolor.z;											
	fResult.x -= fDeltacolor.z*fvalue.x;								
	fResult.y -= fDeltacolor.z*fvalue.x; 								
	saturate(fResult.xyz);												
	fResult += float4(g_param[3], g_param[3], g_param[3], 0);			
	saturate(fResult.xyz);												
	fResult.xyz = g_param[4]*fResult.xyz +g_param[5];					
	saturate(fResult.xyz);												
	output.cr = fResult;												
	return output;														
};																			
