using System;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace ArchBuilder.Revit.UI.Availability
{
    /// <summary>
    /// Availability class that enables commands only when a document is open.
    /// Implements professional workflow controls for ArchBuilder.AI commands.
    /// </summary>
    public class DocumentAvailability : IExternalCommandAvailability
    {
        /// <summary>
        /// Checks if the command is available based on document state.
        /// </summary>
        /// <param name="applicationData">The application data.</param>
        /// <param name="selectedCategories">The selected categories.</param>
        /// <returns>True if command should be available.</returns>
        public bool IsCommandAvailable(UIApplication applicationData, CategorySet selectedCategories)
        {
            try
            {
                // Command is available if there's an active document
                var activeDoc = applicationData?.ActiveUIDocument?.Document;
                
                if (activeDoc == null)
                    return false;

                // Additional checks for document state
                if (activeDoc.IsReadOnly)
                    return false;

                // Check if document is a family document (not supported for layout commands)
                if (activeDoc.IsFamilyDocument)
                    return false;

                return true;
            }
            catch (Exception)
            {
                // If there's any error checking availability, disable the command
                return false;
            }
        }
    }

    /// <summary>
    /// Availability class that enables commands only when elements are selected.
    /// </summary>
    public class SelectionAvailability : IExternalCommandAvailability
    {
        /// <summary>
        /// Checks if the command is available based on selection state.
        /// </summary>
        /// <param name="applicationData">The application data.</param>
        /// <param name="selectedCategories">The selected categories.</param>
        /// <returns>True if command should be available.</returns>
        public bool IsCommandAvailable(UIApplication applicationData, CategorySet selectedCategories)
        {
            try
            {
                var activeUIDoc = applicationData?.ActiveUIDocument;
                if (activeUIDoc?.Document == null)
                    return false;

                // Command is available if there are selected elements
                var selection = activeUIDoc.Selection;
                var selectedIds = selection.GetElementIds();

                return selectedIds != null && selectedIds.Count > 0;
            }
            catch (Exception)
            {
                return false;
            }
        }
    }

    /// <summary>
    /// Availability class for commands that require walls to be selected.
    /// </summary>
    public class WallSelectionAvailability : IExternalCommandAvailability
    {
        /// <summary>
        /// Checks if the command is available based on wall selection.
        /// </summary>
        /// <param name="applicationData">The application data.</param>
        /// <param name="selectedCategories">The selected categories.</param>
        /// <returns>True if walls are selected.</returns>
        public bool IsCommandAvailable(UIApplication applicationData, CategorySet selectedCategories)
        {
            try
            {
                var activeUIDoc = applicationData?.ActiveUIDocument;
                if (activeUIDoc?.Document == null)
                    return false;

                var selection = activeUIDoc.Selection;
                var selectedIds = selection.GetElementIds();

                if (selectedIds == null || selectedIds.Count == 0)
                    return false;

                // Check if at least one selected element is a wall
                foreach (var elementId in selectedIds)
                {
                    var element = activeUIDoc.Document.GetElement(elementId);
                    if (element is Wall)
                        return true;
                }

                return false;
            }
            catch (Exception)
            {
                return false;
            }
        }
    }
}