
" Questions to test the RAG system"

please provide me with a set of question applicable to this document . e.g "how to reset AP"
Gemini response
To help you test your RAG system, here is a set of questions derived from the Operator's Guide, covering various sections and levels of procedural detail:Antenna Positioner (AP) Operations
"How do I reset AP failures for a specific antenna?"
"What is the procedure to move the indexer on an antenna?"
"How can I switch motion profilers on or off?"
"What are the steps for S-band power levelling?"
Receivers (Rx) & Digitisers (Dig)
"How do I switch the LNA power for L-band or U-band?"
"What is the command to stop all streaming digitisers for all antennas?"
"How do I perform a global sync of all digitizers?"
"How can I check which receptors have UHF-band digitisers?"
"What is the process to powercycle a digitizer through telnet?"
Correlator Beamformer (CBF) & Troubleshooting
"How do I check SKARAB health?"
"What is the procedure for UHF network reorder and sync errors on cmc1 and cmc2?"
"How can I set gains to zero for an active subarray?"
"How do I address a 'Double delays' (Abnormal_CBF_1_Update_Rate) issue?"
General Operations & Logs
"What is the command to check the MeerKAT status?"
"How do I find proxy logs for a specific node?"
"What is the procedure to create a subarray in an Ipython session?"
"How do I conduct a pointing check in S-band?"
Would you like me to extract any specific procedures or command sequences to help you verify the accuracy of your RAG model's answers?
This is the conversation for the first 5 questions"--"How do I reset AP failures for a specific antenna? I don't have enough information to provide an answer based on the given context. The context only provides general information about the Antenna Positioner (AP) and fails to mention any specific procedures or commands for resetting AP failures for a particular antenna. > What is the procedure to move the indexer on an antenna? Unfortunately, I couldn't find any information on what the procedure to move the indexer on an antenna is. The context only provides information about stopping a digital capture on the cam.m0XX.req and doesn't mention anything related to moving the indexer. If you need more information, please check the ANTENNA POSITIONER (AP) section or the operator's guide for more details. > How can I switch motion profilers on or off? According to the context, you can switch motion profilers on or off using the following commands: - To enable motion profiling for a specific profile (e.g., elevation or azimuth), use the command: `cam.m0XX.req.ap_enable_motion_profiler('elev', 1)` or `cam.m0XX.req.ap_enable_motion_profiler('azim', 1)`, where 'elev' is replaced with either 'elev' or 'azim'. - To switch motion profilers off on all AP proxies besides Proxy 7 and Proxy 8, the context states that these should be turned on. Source files: Operator's Guide.docx (sections "AP Motion Profilers" and "To switch profilers On") > What are the steps for S-band power levelling? According to the context, the steps for S-band power levelling are as follows: 1. Configure all cameras using `configure_cam('all')`. 2. Define a list of APs that need levelling (`antlist`). 3. Iterate through each antenna in the camera's list (`cam.ants`): - Check if the antenna's name is in the `antlist`. - If it is, set the indexer to S-band using: * `ant.req.mode('STOP')` * `ant.req.select_band('s-band')` Note that the exact steps are not explicitly listed in the provided context, but can be inferred from the code." ---
Gemini response
It appears your RAG system may be struggling with parsing specific code blocks, command sequences, or the hierarchical structure of the document (sections, headings, and lists).

To help you debug, here is a categorized set of questions that target specific sections of the document. These are designed to test if your RAG is retrieving the correct chunks (sections) and correctly interpreting the command sequences within them.Antenna Positioner (AP)
"What is the command sequence to reset AP failures?"
Why this tests RAG: This requires the model to correctly identify the "To reset AP failures" section and retrieve the exact code block (4 lines).
"How do I switch off motion profilers?"
Why this tests RAG: This requires finding a subsection within the "AP Motion Profilers" section.
Receivers (Rx)
"What are the commands to switch on AMPs?"
Why this tests RAG: This tests the model's ability to distinguish between "Switching On AMPs" and "Switching Off AMPs."
Digitizers (Dig)
"How can I mark a digitizer as absent?"
Why this tests RAG: This requires checking the "Powercycle Digitiser" section and potentially identifying the correct band-specific sub-steps.
"What is the command to stop all streaming digitizers for all antennas?"
Why this tests RAG: This tests the model's ability to distinguish between "For an antenna" and "For All antennas."
Correlator Beamformer (CBF)
"How do I set gains to zero for an active subarray?"
Why this tests RAG: This involves navigating to the "Setting gains to zero" section and correctly identifying the command that includes the port number (740x).
"What is the procedure to check SKARAB health?"
Why this tests RAG: This tests the model's ability to retrieve the specific file path (/home/kat/katsdpscripts/utility/) and command sequence.
Observation & Subarray
"What is the instruction set for a pointing check on J0408-6545?"
Why this tests RAG: This requires retrieving a long, complex command string inside a code block in the "Observing in S-band (Pointing Check)" section.
"What are the steps to create a new subarray in an IPython session?"
Why this tests RAG: This tests the model's ability to handle multi-step procedural text and code examples.
Logs
"What is the command to grep proxy logs for antenna m006 for the date 2023-03-11?"
Why this tests RAG: This tests the model's ability to extract specific examples provided in the "Logs On Portal" section.
Debugging Tip: If your RAG system is failing these, check your chunking strategy. If the code blocks are being split across different chunks, the model will likely struggle to provide the full command sequence or context. You might need to ensure that your chunker keeps "procedure" headings and their associated code blocks together.