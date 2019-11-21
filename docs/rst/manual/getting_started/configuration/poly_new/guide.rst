Creating a config
=================
ERT runs a set of simulations with prior set of parameters sampled from distributions. The results of the simulations are then given to an optimization algorithm. The algorithm then uses a set of observations to tune the parameters. Using the updated parameters for the next run of the simulations will give results that fit better with the set of observations.

To understand the basics of how to configure and use ERT, we will walk through how to set up a project that uses a polynomial evaluation as the forward model.

Minimal config
--------------
In order to test that our setup is working, we will create the minimal configuration we need in order to lauch the Graphical user interface and run an empty experiment that does nothing. First create a folder with the name "poly_example". 

Create a config
***************
Then create a file "poly.ert" inside the folder with the following content:

    .. literalinclude:: minimal/poly.ert

* :ref:`JOBNAME <jobname>` Specifies the name for each simulation. The %d will be replaced with the simulation number, so that the jobs will be called poly_0, poly_1, etc.
* :ref:`NUM_REALIZATIONS <num_realizations>` We have to specify how many simulation we want. The word realization relates to the mathematical concept of an actual observation from a distribution.
* :ref:`QUEUE_SYSTEM <QUEUE_SYSTEM>` Finally, we must specify where each simulation is to run, which is handled by the queue system. LOCAL means that everything will run on you local computer. Other possibilites are LSF and TORQUE, which are queuing systems. To use these you must have an environment available where this is supported and configured.

Launch the user interface
*************************

Navigate to this folder on your command line and run ERT::

    ert gui poly.ert

Wait a while and ERT will launch. You will see a warning because we haven't configured any observarions yet. This is expected, so click OK. You will see the main ERT user inteface screen.

.. image:: minimal/ert.png

On the main screen you can see some elements. The ones we care about in this Guide are:

* Simulation mode: lets you choose between running a single realization, or running all or specify a subset of them.
* Runpath: shows wehere each realization of the experiment will be executed. The "%d" in this path is replaced by the number of the realization. Here we see a default used, since we have not configured the runpath yet.
* The Configuration summary will show us what we have configured, and is empty at this moment.
* The Start Simulation button will start an experiment with the current configuration and simulation mode.

Run an empty experiment
***********************
To run an empty experiment, select "Ensamble experiment" as the Simulation mode. Then press the "Start simulation" button. You get a dialog asking if you want to start with the "default" case. That is fine, so press "Yes". The experiment will run, but since we have configured no forward model, only an empty experiment is executed.

A new window will appear called "Simulations". Here you can see the status of the running of the experiment. If you press "Details", you can see status of each running realization.

.. image:: minimal/simulations.png

As it's running you can see that not all the realizations are running at the
same time. There is an upper limit to how many realizations can run at the same
time, which is decided by the queue. You will probably have 2 running at a time.
We will configure this at a later stage. When all the realizations are done,
close all the ERT windows.

Inspect the results
*******************
Now in the project folder there should be two new folders, "simulations" and "storage". Storage is ERT's internal data, and should not be touched. The "simulations" folder is created based on the RUNPATH configuration. If you open this folder you will see one folder for each realization, labeled realization0, realization1, etc. Inside each of these folders is where each realization has run. If you look inside, you will see a few files that ERT uses to keep track of the jobs. 

* jobs.json: defines the jobs to run
* OK: indicates success. On error EXIT and ERROR file is created instead.
* STATUS: legacy status file
* status.json: used to communicate status to the ERT user interface.

You should not touch these files, either manually, or as part of the jobs your experiments define.

Adding a Forward Model and Runpath
----------------------------------
The example project will use a simple polynomial evaluation as the forward model. In real experiments this would usually be running a simulator, like Eclipe, instead. The forward model is implemented as a simple python script "poly_eval.py". We will start with a simple script just to check that we can run it. Later we will expand on it and the configuration file to introduce some fundamental features of ERT.

Add a Runpath
*************
In the minimal config, we used the default :ref:`RUNPATH <runpath>` which ran the realization in simulations/realization%d. This is not sufficient for running the algorithms of ERT. When running the algorithms of ERT, we must usually run the Ensamble several times, and the runpath needs to reflect this. We need to have each iteration run in a different forder, so that they won't step on each others toes. Add to the config ("poly.ert") file the following line::

    RUNPATH poly_out/real_%d/iter_%d

The second "%d" in the runpath will be replaced by the iteration of running the ensamble. In this way we can run several times, and have the results in different folders.

Create script
*************
In a file "poly_eval.py" put the following:

    .. include:: with_simple_script/poly_eval.py
        :code:

For now, this script evaluates a polynomial with fixed coefficients. The coefficients are stored in a dictionary with keys a, b and c. Later we will see how to have these values injected by ERT. The script evaluates at fixed points from 0 to 9. After evaluation, the script writes the results to a file called "poly_0.out".

Mark the script as executable
*****************************
You have to mark the file as executable. In the terminal you can do this by running the following command::

    chmod +x poly_eval.py

Add a Job Definition and add it to the Simulation jobs
******************************************************
The definition of a job is written in a separate file. In our case we only need to specify the executable name. Create a file called "POLY_EVAL" with the following content:

    .. include:: with_simple_script/POLY_EVAL

Now we must refer to this job definition in the configuration. Add the line::

    INSTALL_JOB poly_eval POLY_EVAL 
    SIMULATION_JOB poly_eval

The :ref:`INSTALL_JOB <install_job>` line tells ERT the name of the job "poly_eval", and then the file in which to find the details of how to run the job. The :ref:`SIMULATION_JOB <simulation_job>` line tells ERT to run the job as part of the simulation run.

Now the config file should look like this:

    .. include:: with_simple_script/poly.ert
        :code:

Running with the new Job
************************
Before we run again delete the old output files by running the command::

    rm -r simulations

Now start up ERT by again running "ert gui poly.ert". The main window should now reflect the new runpath:

    .. image:: with_simple_script/ert.png

You can see in the configuration view that there is now a forward model. And you can also see that the runpath has changed from the default to what we specified in the config. Now run the ensamble experimet again like you did earlier. After it has finished, close all ERT windows.

In you project folder you should now see a new folder called "poly_out" as you defined in the RUNPATH configuration. Inside the folder yo will see folders named "real_0", "real_1", and so on, for each realization. Inside these folders you will see a new level of folders named "iter_0", where the realization simulation has run. Inside this folder, you will see some new files in addition to those you saw before. 

* poly_eval.stderr.0 - errors that the poly_eval.py script writes to the standard error output
* poly_eval.stdout.0 - normal output that the poly_eval.py scrips wrote to the standard output
* poly_0.out - the file that the script writes the results to. This is specific to the script, and not created by ERT, and different files will be written by different jobs.

If you look at the "poly_0.out" file in each of the runpaths (e.g. run "cat poly_out/real_0/iter_0/poly_0.out"), you should see the following in all the files::

    3
    6
    11
    18
    27
    38
    51
    66
    83
    102

It is of course not very useful that all the realization simulations evaluate the same mode. In the next step we will use ERT to automatically sample parameters for the realizations (i.e. coefficients for the polynomials), and read them in the poly_eval.py script.

Creating paramaters
-------------------
In order to set up parameters in ERT, we need to create a file with description of the distribution of the parameters. This is called the priors. Then we specify where ERT can find this file, and how to instantiate it into each simulation runpath via templating mechanism. The templating mechanism lets you specify a file in the format you desire, in which ERT will put the parameters by replacing certain placeholders with the actual parameters sampled from the distributions.

Adding prior distributions
**************************
To description the prior distributions, create a file "coeff_priors" with the following content:

    .. include:: with_parameters/coeff_priors
        :code:

In this file we list each parameter line by line. The first part of a line is the name of the parameter. Following this is the type of distribution we want to sample the parameter from. Here we choose a uniform distribution. Following the distribution type, are the arguments describing the distribution. In the case of UNIFORM there are two parameters denoting the lower and upper bound of the distribution. Other distributions have different arguments.

Adding a template
*****************
Then we create a template into which the samples from the distributions will be put. Create a file called "coeff.tmpl" and put the following content:

    .. include:: with_parameters/coeff.tmpl
        :code:

The text within angled brackets (< and >), will be replaced by the samples from the corresponding distribution from the coeff_priors file. The result will be put in a file with a name we specify in the configuration.

Configuring the parameter set and and corresponding template
************************************************************
Now, put the line "GEN_KW COEFFS coeff.tmpl coeffs.json coeff_priors" into the config file "poly.ert".

The :ref:`GEN_KW <gen_kw>` keyword tells ERT to generate parameters from a distribution. After the keyword there follows four arguments, specifying how to do this.

 1. COEFFS - The first argument is the name you wish to give to give to the parameter set. 
 2. coeff.tmpl - The second argument is the name of the template file with placeholder names of the parameters. 
 3. coeffs.json - The third argument is the name of the file into which the result of the template replacement will be written in each simulation runpath before the simulation jobs run. 
 4. coeff_priors - The fourth and final argument specifies where the paramter distributions are specified.

Reading parameters in simulation script
***************************************
We need to change the simulation script so that it reads the "coeffs.json" file that ERT writes the samlped parameters in. Change the script "poly_eval.py" to the following:

    .. literalinclude:: with_parameters/poly_eval.py

Increasing the number of realizations
*************************************
Let us also increase the number of realizations now, so that we get a larger sample size, and thus have more data to inspect in the graphical user interface.

Increase the NUM_REALIZATIONS value to 100. This will make us run 100 simulations. We can also specify that we want to run more simultaneous simulations, so it will run faster. This is configured in the queue system by specifying a :ref:`queue option <queue_option>` "MAX_RUNNING" for the "LOCAL" queue, like this: "QUEUE_OPTION LOCAL MAX_RUNNING 50".

After adding these two lines and changing the number of realizations, the config should look like this:

    .. include:: with_parameters/poly.ert
        :code:

Running vith sampled parameters
*******************************
Now you should delete the "storage" and "poly_out" folders from last run, so we know we are getting only new data.

Launch ERT again. Notice that the config summary now specifies the name of the parameter set we defined. Then select Ensamble Experiment in the simulation mode, and start the simulation.

When the simulations are done, you can now press the "Create Plot" button in the progress window or in the main window, and the Plotting window should open. Here you can now see the distributions of the three different parameters we created. They are named "COEFFS:COEFF_A", "COEFFS:COEFF_B" and "COEFFS:COEFF_C", with the parameter set name first, then a colon and then the name of the specific paramter.

You should see something similar to this:

    .. image:: with_parameters/plots.png

Play around and look at the different plots.

Inspecting the paramters and results
************************************
Inside each of the runpaths you should now be able to find the instantiated paramter template files "coeffs.json". Looking at them (e.g. with "cat poly_out/real_4/iter_0/coeffs.json") you should see something like this::

    {
        "a": 0.830303,
        "b": 1.69181,
        "c": 0.114524
    }

If you now look at the generated file "poly_0.out" in the runpaths you should also see that each simulation has yielded different results. Here is one possible output from running "cat poly_out/real_0/iter_0/poly_0.out"::
        
    2.23622
    4.288035
    6.83408
    9.874355
    13.40886
    17.437595
    21.96056
    26.977755
    32.48918
    38.494835

In the next section, we will see how to describe the results to ERT, and how to specify some observations that we wish ERT to optimise towards.

Reading simulation results
--------------------------
We have to tell ERT where to find the results of our simulations. For general data like we have in this example, we use the :ref:`GEN_DATA <gen_data>` keyword. Add this lineto the "poly.ert" file::

    GEN_DATA POLY_RES RESULT_FILE:poly_%d.out REPORT_STEPS:0 INPUT_FORMAT:ASCII

The arguments of GEN_DATA:

    1. POLY_RES - Name of this result set.
    2. RESULT_FILE:poly_%d.out - File with results of simulation. The %d is always 0, but needs to be specified. (it was used in earlier ERT versions)
    3. REPORT_STEPS:0 - TODO
    4. INPUT_FORMAT:ASCII - Specifies that the file is a normal text file (ASCII stands for "American Standard Code for Information Interchange")

The config file should now look like this:

    .. literalinclude :: with_results/poly.ert

If you now run the ensamble experiment again, and then open the plot view, you should see a new plot available called POLY_RES:

    .. image :: with_results/poly_plot.png

Adding observations
-------------------
In order to use the update algorithms of ERT, we need to have some observations to which the results can be compared, so that ERT can tune the parameters to make the models better fit the observed data.

The observations need to relate to some results of the simulation, so that the algorithms can compare them. We have some observations from the polynomial that were measured at the points 0, 2, 4, 6 and 8. The indices here happen to align with the x values of the polynomial evaluation, but this is incidental. Usually the indices are only the order of the observations in the file. Put the following observations in the file poly_obs_data.txt:

    .. literalinclude:: with_observations/poly_obs_data.txt

The observations are written one for each line, with the first number signifying the observed value, and the second number signifying the uncertainty

Now lets describe the observations we have to ERT. This is done with the :ref:`OBS_CONFIG <obs_config>` keyword, which refers to a file in which we must describe the observations. Firs, make a file called "observations" in the project folder with the following content:

    .. literalinclude:: with_observations/observations

The GENERAL_OBSERVATION keyword tells ERT about how to find results, and how to relate them to a result set. It is followed by a name of the observation set, then a list of key-value pairs specifying the details.

* DATA - specifies which result set to relate the observation to
* INDEX_LIST - In our results file we have 10 values, while we only have 5 observation. This list tells ERT which of the results we have observations for. If they are the same length, you can omit this
* RESTART - legacy, must simply be the same as REPORT_STEPS from the GEN_DATA line.
* OBS_FILE - the file in which the observations can be found.

After creating the observations file we need to add it to the config file with these lines::

    OBS_CONFIG observations
    TIME_MAP time_map

The :ref:`OBS_CONFIG <obs_config>` line simply tells ERT that there is a description of an observation set in the file "observations". The :ref:`TIME_MAP <time_map>` is legacy, and not used anymore, but it is still required when we have an observation set.

If you now lauch ERT again you will now be able to choose different simulation modes. Choose Ensamble Smoother, and start the simulations. When it it is running you will see that when the first set of realizations is done, a new tab is created, where another set of realizations is visualised. This new set runs with the updated parameters that the algorithm creates, which should give new results that better fit with the observations.

If you open the Plotting window when the simulations are done, you will see the POLY_RES plot is shown with a yellow background, because it now has observations attached. When showing the POLY_RES plot, you will see the observations we specified, visualized as black dots representing the observed values, and black lines extending up and down, representing the uncertainty. You can also view plots belonging to the different iterations of the ensamble. To do this click "Add case to plot", and select "default" as the first plot, and "default_smoother_update" as the second. They will be shown in different colours. You should now see the updated values are fitting better to the observations, as in the picture below:

.. image:: with_observations/plot_obs.png

Now you know the basics ERT configuration. There are many more details in the rest of the documentation which you can refer to when you need.





